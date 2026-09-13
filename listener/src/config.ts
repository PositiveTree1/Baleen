import dotenv from 'dotenv';
import path from 'path';

// Load from root .env.local if present
dotenv.config({ path: path.resolve(__dirname, '../../.env.local') });

export const config = {
  ENVIO_API_KEY: process.env.ENVIO_API_KEY || '',
  DATABASE_URL: process.env.DATABASE_URL || '',
  BACKEND_URL: process.env.BACKEND_URL || (process.env.PORT ? `http://127.0.0.1:${process.env.PORT}` : 'http://127.0.0.1:8000'),
  LISTENER_SERVICE_KEY: process.env.LISTENER_SERVICE_KEY || 'baleen_internal_listener_key_2026',
};
