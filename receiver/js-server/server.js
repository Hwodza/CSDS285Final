const express = require('express');
const WebSocket = require('ws');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { open } = require('sqlite');

const app = express();
const port = 8080;

// Database setup
async function setupDatabase() {
    const db = await open({
        filename: './devices.db',
        driver: sqlite3.Database
    });

    await db.exec(`
        CREATE TABLE IF NOT EXISTS device_stats (
            device_id TEXT,
            timestamp INTEGER,
            cpu_usage_percent REAL,
            kbmemfree TEXT,
            kbmemused TEXT,
            memused_percent TEXT,
            network_data TEXT,
            disk_data TEXT,
            PRIMARY KEY (device_id, timestamp)
        )
    `);

    return db;
}

// Initialize server
async function startServer() {
    const db = await setupDatabase();
    console.log('Database initialized');

    app.use(express.static('public'));
    app.use(express.json());

    const server = app.listen(port, () => {
        console.log(`Server running at http://localhost:${port}`);
    });

    const wss = new WebSocket.Server({ server });
    const recentDeviceData = new Map();

    function validateData(data) {
        return data && 
               data.id && 
               data.timestamp && 
               data.cpu_usage_percent !== undefined &&
               data.memory &&
               data.network &&
               data.disk;
    }

    async function storeDeviceData(data) {
        try {
            await db.run(`
                INSERT OR REPLACE INTO device_stats (
                    device_id, timestamp, cpu_usage_percent,
                    kbmemfree, kbmemused, memused_percent,
                    network_data, disk_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    data.id,
                    data.timestamp,
                    data.cpu_usage_percent,
                    data.memory.kbmemfree,
                    data.memory.kbmemused,
                    data.memory.memused_percent,
                    JSON.stringify(data.network),
                    JSON.stringify(data.disk)
                ]
            );
        } catch (err) {
            console.error('Database error:', err);
            throw err;
        }
    }

    wss.on('connection', (ws) => {
        console.log('New client connected');
        
        // Send recent data to new client
        recentDeviceData.forEach((data, id) => {
            ws.send(JSON.stringify({
                type: 'device_update',
                id: id,
                data: data
            }));
        });

        ws.on('message', async (message) => {
            try {
                const data = JSON.parse(message);
                if (validateData(data)) {
                    await storeDeviceData(data);
                    recentDeviceData.set(data.id, data);
                    broadcastDeviceUpdate(data.id);
                }
            } catch (e) {
                console.error('Error processing message:', e);
            }
        });
    });

    function broadcastDeviceUpdate(deviceId) {
        const deviceData = recentDeviceData.get(deviceId);
        if (!deviceData) return;

        const updateMessage = JSON.stringify({
            type: 'device_update',
            id: deviceId,
            data: deviceData
        });

        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(updateMessage);
            }
        });
    }

    // API Endpoints
    app.post('/data', async (req, res) => {
        try {
            const data = req.body;
            if (validateData(data)) {
                await storeDeviceData(data);
                recentDeviceData.set(data.id, data);
                broadcastDeviceUpdate(data.id);
                res.json({ status: 'success', id: data.id });
            } else {
                res.status(400).json({ error: 'Invalid data format' });
            }
        } catch (e) {
            res.status(500).json({ error: 'Server error' });
        }
    });

    app.get('/devices', async (req, res) => {
        try {
            const devices = await db.all('SELECT DISTINCT device_id FROM device_stats');
            res.json(devices.map(d => d.device_id));
        } catch (e) {
            res.status(500).json({ error: 'Database error' });
        }
    });

    app.get('/data/:id', async (req, res) => {
        try {
            const { id } = req.params;
            const limit = parseInt(req.query.limit) || 100;
            
            const rows = await db.all(
                `SELECT * FROM device_stats 
                 WHERE device_id = ? 
                 ORDER BY timestamp DESC 
                 LIMIT ?`,
                [id, limit]
            );

            const result = rows.map(row => ({
                ...row,
                network: JSON.parse(row.network_data),
                disk: JSON.parse(row.disk_data)
            }));

            res.json(result);
        } catch (e) {
            res.status(500).json({ error: 'Database error' });
        }
    });
    app.get('/device/:id', (req, res) => {
        res.sendFile(path.join(__dirname, 'public', 'device.html'));
    });

    app.get('/api/device/:id/history', async (req, res) => {
        try {
            const { id } = req.params;
            const hours = parseInt(req.query.hours) || 24;
            const cutoff = Math.floor(Date.now() / 1000) - (hours * 3600);

            const rows = await db.all(`
                SELECT * FROM device_stats
                WHERE device_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC`,
                [id, cutoff]
            );

            const result = {
                timestamps: [],
                cpu: [],
                memory: [],
                network: {},
                disk: {}
            };

            // Initialize network interfaces
            if (rows.length > 0) {
                const first = JSON.parse(rows[0].network_data);
                first.forEach(iface => {
                    result.network[iface.iface] = { rx: [], tx: [] };
                });
            }

            rows.forEach(row => {
                const time = new Date(row.timestamp * 1000);
                result.timestamps.push(time.toLocaleTimeString());

                // CPU data
                result.cpu.push(row.cpu_usage_percent);

                // Memory data
                result.memory.push({
                    free: row.kbmemfree,
                    used: row.kbmemused,
                    percent: row.memused_percent
                });

                // Network data
                const network = JSON.parse(row.network_data);
                network.forEach(iface => {
                    if (result.network[iface.iface]) {
                        result.network[iface.iface].rx.push(iface.rx_kb);
                        result.network[iface.iface].tx.push(iface.tx_kb);
                    }
                });

                // Disk data (simplified example)
                const disk = JSON.parse(row.disk_data);
                disk.forEach(d => {
                    if (!result.disk[d.device]) {
                        result.disk[d.device] = { wait: [], util: [] };
                    }
                    result.disk[d.device].wait.push(d.wait);
                    result.disk[d.device].util.push(d.util);
                });
            });

            res.json(result);
        } catch (e) {
            console.error('Error fetching history:', e);
            res.status(500).json({ error: 'Server error' });
        }
    });

    app.get('/', (req, res) => {
        res.sendFile(path.join(__dirname, 'public', 'index.html'));
    });

    // Cleanup on exit
    process.on('SIGINT', async () => {
        await db.close();
        process.exit();
    });
}

startServer().catch(err => {
    console.error('Server startup error:', err);
    process.exit(1);
});
