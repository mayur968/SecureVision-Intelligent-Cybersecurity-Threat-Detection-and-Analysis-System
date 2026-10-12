import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import pino from 'pino';
import pinoHttp from 'pino-http';
import routes from './routes/index.js';
import { errorHandler, notFound } from './middleware/errorHandler.js';

// ── Logger (exported so middleware can import it) ─────────────────────────────
export const logger = pino({ level: process.env.LOG_LEVEL ?? 'info' });

// ── App ───────────────────────────────────────────────────────────────────────
const app  = express();
const PORT = parseInt(process.env.PORT ?? '4000', 10);
const CLIENT_ORIGIN = process.env.CLIENT_ORIGIN ?? 'http://localhost:5173';

// Security
app.use(helmet());
app.use(cors({ origin: CLIENT_ORIGIN, credentials: false }));

// Logging
app.use(pinoHttp({ logger }));

// Body parsing
app.use(express.json({ limit: '1mb' }));

// Rate limiting — global: 200 req / 15 min per IP
app.use(rateLimit({
  windowMs:  15 * 60 * 1000,
  max:        200,
  standardHeaders: true,
  legacyHeaders:   false,
  message: { success: false, error: 'Too many requests, please slow down.' },
}));

// Scan-specific rate limit: 30 scans / 60 s
const scanLimiter = rateLimit({
  windowMs: 60_000,
  max:       30,
  message: { success: false, error: 'Scan rate limit exceeded. Wait 60 seconds.' },
});
app.use('/api/scan', scanLimiter);

// Routes
app.use('/api', routes);

// 404 + error handling (must be last)
app.use(notFound);
app.use(errorHandler);

app.listen(PORT, () => {
  logger.info(`SecureVision gateway listening on http://localhost:${PORT}`);
  logger.info(`Proxying ML service at ${process.env.ML_SERVICE_URL ?? 'http://localhost:5000'}`);
});

export default app;
