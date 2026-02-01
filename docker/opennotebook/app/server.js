const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
const PORT = process.env.PORT || 8080;

// Security middleware
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({
      status: 'ok',
      service: 'opennotebook',
      timestamp: new Date().toISOString(),
      database: 'connected'
    });
  } catch (error) {
    res.status(503).json({
      status: 'error',
      service: 'opennotebook',
      timestamp: new Date().toISOString(),
      database: 'disconnected',
      error: error.message
    });
  }
});

// API routes placeholder
app.get('/api/v1/notebooks', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM opennotebook.notebooks ORDER BY created_at DESC LIMIT 10');
    res.json({
      success: true,
      data: result.rows
    });
  } catch (error) {
    console.error('Error fetching notebooks:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch notebooks'
    });
  }
});

app.post('/api/v1/notebooks', async (req, res) => {
  const { title, content } = req.body;

  if (!title) {
    return res.status(400).json({
      success: false,
      error: 'Title is required'
    });
  }

  try {
    const result = await pool.query(
      'INSERT INTO opennotebook.notebooks (title, content) VALUES ($1, $2) RETURNING *',
      [title, content || '']
    );
    res.status(201).json({
      success: true,
      data: result.rows[0]
    });
  } catch (error) {
    console.error('Error creating notebook:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create notebook'
    });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Not found'
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM signal received: closing HTTP server');
  await pool.end();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT signal received: closing HTTP server');
  await pool.end();
  process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenNotebook server listening on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`Database: ${process.env.DATABASE_URL ? 'configured' : 'not configured'}`);
});
