import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as ml from '../services/mlClient.js';

// ── Input schemas ──────────────────────────────────────────────────────────────

const UrlBody    = z.object({ url:     z.string().url().max(2048) });
const MessageBody= z.object({ message: z.string().min(10).max(10_000) });

// ── Handlers ───────────────────────────────────────────────────────────────────

export async function scanUrl(req: Request, res: Response, next: NextFunction) {
  try {
    const { url } = UrlBody.parse(req.body);
    const result  = await ml.scanUrl(url);
    res.json(result);
  } catch (err) {
    next(err);
  }
}

export async function scanMessage(req: Request, res: Response, next: NextFunction) {
  try {
    const { message } = MessageBody.parse(req.body);
    const result      = await ml.scanMessage(message);
    res.json(result);
  } catch (err) {
    next(err);
  }
}

export async function scanApk(req: Request, res: Response, next: NextFunction) {
  try {
    const file = req.file;
    if (!file) {
      res.status(400).json({ success: false, error: 'No file uploaded' });
      return;
    }

    const result = await ml.scanApk(file.buffer, file.originalname, file.mimetype);
    res.json(result);
  } catch (err) {
    next(err);
  }
}

export async function getHistory(req: Request, res: Response, next: NextFunction) {
  try {
    const limit  = Math.min(Number(req.query.limit) || 50, 100);
    const result = await ml.getHistory(limit);
    res.json({ success: true, ...result });
  } catch (err) {
    next(err);
  }
}

export async function getStatistics(_req: Request, res: Response, next: NextFunction) {
  try {
    const stats = await ml.getStatistics();
    res.json({ success: true, statistics: stats });
  } catch (err) {
    next(err);
  }
}

export async function healthCheck(_req: Request, res: Response, next: NextFunction) {
  try {
    const health = await ml.getHealth();
    res.json({ success: true, gateway: 'ok', ml: health });
  } catch (err) {
    next(err);
  }
}

export const startLiveScanHandler = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const schema = z.object({ url: z.string().url('Must be a valid URL').max(2048) });
    const { url } = schema.parse(req.body);
    const data = await ml.startLiveScan(url);
    res.status(202).json(data);
  } catch (err) {
    next(err);
  }
};

export const getLiveScanJobHandler = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const { jobId } = req.params;
    const data = await ml.getLiveScanJob(jobId);
    res.json(data);
  } catch (err) {
    next(err);
  }
};
