const express = require('express');
const WebSocket = require('ws');
const path = require('path');

const app = express();
const port = 8080;

// Serve static files (our HTML)
app.use(express.static('public'));

// Create HTTP server
const server = app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});

// Create WebSocket server
const wss = new WebSocket.Server({ server });

// Store connected clients
const clients = new Set();

wss.on('connection', (ws) => {
    console.log('New client connected');

    ws.on('close', (code, reason) => {
        console.log(`Client disconnected. Code: ${code}, Reason: ${reason}`);
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
    clients.add(ws);
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            // Only broadcast if the data has an ID field
            if (data.id !== undefined) {
                // Broadcast to all clients
                for (const client of clients) {
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(JSON.stringify(data));
                    }
                }
            }
        } catch (e) {
            console.error('Error processing message:', e);
        }
    });
    
    ws.on('close', () => {
        console.log('Client disconnected');
        clients.delete(ws);
    });
});

// Serve the HTML page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Also accept JSON data via HTTP POST (for compatibility)
app.post('/data', express.json(), (req, res) => {
    const data = req.body;
    
    if (data && data.id !== undefined) {
        // Broadcast to all WebSocket clients
        for (const client of clients) {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(data));
            }
        }
        
        res.json({ message: "Data received successfully", data: data });
    } else {
        res.status(400).json({ error: "Invalid JSON or missing ID field" });
    }
});
