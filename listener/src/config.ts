import dotenv from 'dotenv';
import path from 'path';

// Load from root .env.local if present
dotenv.config({ path: path.resolve(__dirname, '../../.env.local') });

export const config = {
  ENVIO_API_KEY: process.env.ENVIO_API_KEY || '',
  DATABASE_URL: process.env.DATABASE_URL || '',
  BACKEND_URL: process.env.BACKEND_URL || 'https://baleen-backend-k32g.onrender.com',
};
