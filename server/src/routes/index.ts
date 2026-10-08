import { Router } from 'express';
import multer from 'multer';
import rateLimit from 'express-rate-limit';
import * as ctrl from '../controllers/scanController.js';

const router  = Router();
// multer: keep file in memory, max 50 MB, APK only
const upload  = multer({
  storage: multer.memoryStorage(),
  limits:  { fileSize: 50 * 1024 * 1024 },
  fileFilter(_req, file, cb) {
    if (file.originalname.toLowerCase().endsWith('.apk')) cb(null, true);
    else cb(new Error('Only .apk files are accepted'));
  },
});

const liveScanLimiter = rateLimit({
  windowMs: 60 * 1000,   // 1 minute
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many live scan requests. Maximum 5 per minute.' },
});

router.get ('/health',              ctrl.healthCheck);
router.post('/scan/url',            ctrl.scanUrl);
router.post('/scan/message',        ctrl.scanMessage);
router.post('/scan/apk',            upload.single('file'), ctrl.scanApk);
router.get ('/history',             ctrl.getHistory);
router.get ('/statistics',          ctrl.getStatistics);
router.post('/scan/url/live',       liveScanLimiter, ctrl.startLiveScanHandler);
router.get ('/scan/url/live/:jobId', ctrl.getLiveScanJobHandler);

export default router;
