import { Request, Response, NextFunction } from 'express';
import { ZodError } from 'zod';
import { AxiosError } from 'axios';
import { logger } from '../index.js';

export function errorHandler(
  err: unknown,
  req: Request,
  res: Response,
  _next: NextFunction,
): void {
  // Zod validation errors
  if (err instanceof ZodError) {
    res.status(400).json({
      success: false,
      error: 'Validation error',
      details: err.errors.map((e) => `${e.path.join('.')}: ${e.message}`),
    });
    return;
  }

  // Axios errors forwarding from ML service
  if (err instanceof AxiosError) {
    const status = err.response?.status ?? 502;
    const message = (err.response?.data as { error?: string })?.error
      ?? 'ML service unavailable';
    logger.error({ err, url: req.url }, `ML service error: ${message}`);
    res.status(status).json({ success: false, error: message });
    return;
  }

  // Generic
  logger.error({ err, url: req.url }, 'Unhandled error');
  res.status(500).json({ success: false, error: 'Internal server error' });
}

export function notFound(req: Request, res: Response): void {
  res.status(404).json({ success: false, error: `Route ${req.method} ${req.path} not found` });
}
