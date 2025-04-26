import express, { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import path from 'path';
import fs from 'fs/promises';
import cors from 'cors';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;
const CONTENT_DIR = path.resolve(__dirname, '../../../content/content_ready');
const SCORES_PATH = path.resolve(__dirname, '../../../content/scores.json');
const LOG_PATH = path.resolve(__dirname, '../../../logs/security.log');
const SECRET_KEY = process.env.SECRET_KEY || 'JWT_SECRET';

app.use(cors());
app.use(express.json());

// Mock user database
const users = [
  { id: 1, email: 'test@vaani.com', password: 'password123' },
];

// Middleware to authenticate JWT
function authenticateToken(req: Request, res: Response, next: NextFunction): void {
  let token: string | undefined;
  const authHeader = req.headers['authorization'];
  if (authHeader) {
    token = authHeader.split(' ')[1];
  } else {
    token = req.query.token as string;
  }
  console.log(`[${req.method} ${req.path}] Auth header:`, authHeader);
  console.log(`[${req.method} ${req.path}] Token:`, token);

  if (!token) {
    console.warn(`[${req.method} ${req.path}] No token provided`);
    res.status(401).json({ message: 'Access token missing' });
    return;
  }

  jwt.verify(token, SECRET_KEY, (err, user) => {
    if (err) {
      console.error(`[${req.method} ${req.path}] Token verification failed:`, err.message);
      res.status(403).json({ message: 'Invalid or expired token' });
      return;
    }
    console.log(`[${req.method} ${req.path}] Token verified, user:`, user);
    (req as any).user = user;
    next();
  });
}

// Login endpoint
app.post('/api/login', (req: Request, res: Response): void => {
  const { email, password } = req.body;
  console.log('Login attempt:', { email });
  const user = users.find((u) => u.email === email && u.password === password);
  if (!user) {
    console.warn('Invalid credentials for email:', email);
    res.status(401).json({ message: 'Invalid credentials' });
    return;
  }

  const token = jwt.sign({ id: user.id, email: user.email }, SECRET_KEY, { expiresIn: '1h' });
  console.log('Generated token for user:', email);
  res.json({ token });
});

// Get content files
app.get('/api/content', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    console.log('Fetching content from:', CONTENT_DIR);
    try {
      await fs.access(CONTENT_DIR);
      const files = await fs.readdir(CONTENT_DIR);
      console.log('Files found:', files);

      const contentItems = [];
      for (const file of files) {
        const parts = file.split(/[_|.]/);
        console.log(`File: ${file}, Parts: ${JSON.stringify(parts)}, Is Valid: ${parts.length >= 4}`);
        if (parts.length < 4) continue;

        const [type, id, date, time] = parts;
        if (!['post', 'tweet', 'voice'].includes(type)) continue;

        const filePath = path.join(CONTENT_DIR, file);
        const timestamp = `${date}_${time}`;
        let content: string | undefined;
        let contentType: string = type;

        if (file.endsWith('.json')) {
          const fileContent = await fs.readFile(filePath, 'utf-8');
          const jsonContent = JSON.parse(fileContent);
          content = jsonContent[type === 'voice' ? 'voice_script' : type];
          if (type === 'voice') contentType = 'voice_script';
        } else if (file.endsWith('.mp3')) {
          contentType = 'voice';
        }

        console.log(`File: ${file}, Content Key: ${type === 'voice' ? 'voice_script' : type}, Content: ${content}`);
        contentItems.push({
          id,
          type: contentType,
          content,
          url: `http://localhost:${PORT}/content/${file}`,
          timestamp,
        });
      }

      console.log('Content items to return:', contentItems);
      res.json(contentItems);
    } catch (accessError) {
      console.warn('content_ready directory not found, returning empty content');
      res.json([]);
    }
  } catch (error) {
    console.error('Error in /api/content:', error);
    res.status(500).json({ message: 'Failed to load content', error: (error as Error).message });
  }
});

// Serve content files
app.get('/content/:filename', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  const filename = req.params.filename;
  const filePath = path.join(CONTENT_DIR, filename);
  console.log('Serving file:', filePath);
  try {
    await fs.access(filePath);
    res.sendFile(filePath, {
      headers: {
        'Content-Type': filePath.endsWith('.mp3') ? 'audio/mpeg' : 'application/json',
      },
    });
  } catch (error) {
    console.error('Error serving file:', error);
    res.status(404).json({ message: 'File not found' });
  }
});

// Get scores
app.get('/api/scores', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    console.log('Fetching scores from:', SCORES_PATH);
    try {
      await fs.access(SCORES_PATH);
      const scores = JSON.parse(await fs.readFile(SCORES_PATH, 'utf-8'));
      console.log('Scores loaded:', scores);
      res.json(scores);
    } catch (accessError) {
      console.warn('scores.json not found, returning empty scores');
      res.json([]);
    }
  } catch (error) {
    console.error('Error in /api/scores:', error);
    res.status(500).json({ message: 'Failed to load scores', error: (error as Error).message });
  }
});

// Fetch alerts from security.log
app.get('/api/alerts', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    console.log('Fetching alerts from:', LOG_PATH);
    try {
      await fs.access(LOG_PATH); // Check if file exists
      const logContent = await fs.readFile(LOG_PATH, 'utf-8');
      const alerts = logContent
        .split('\n')
        .filter((line) => line.includes('WARNING') && line.includes('Controversial content detected'))
        .map((line) => {
          const [, timestamp, , , , message] = line.split(' - ');
          return { timestamp, message };
        });
      console.log('Alerts loaded:', alerts);
      res.json(alerts);
    } catch (accessError) {
      console.warn('security.log not found, returning empty alerts');
      res.json([]);
    }
  } catch (error) {
    console.error('Error in /api/alerts:', error);
    res.status(500).json({ message: 'Failed to load alerts', error: (error as Error).message });
  }
});

// Mock Instagram endpoint
app.post('/instagram/post', authenticateToken, (req: Request, res: Response): void => {
  const { contentId } = req.body;
  console.log(`Publishing content ${contentId} to Instagram`);
  res.json({ message: `Content ${contentId} published to Instagram` });
});

// Mock Twitter endpoint
app.post('/twitter/post', authenticateToken, (req: Request, res: Response): void => {
  const { contentId } = req.body;
  console.log(`Publishing content ${contentId} to Twitter`);
  res.json({ message: `Content ${contentId} published to Twitter` });
});

// Mock Spotify endpoint
app.post('/spotify/upload', authenticateToken, (req: Request, res: Response): void => {
  const { contentId } = req.body;
  console.log(`Publishing content ${contentId} to Spotify`);
  res.json({ message: `Content ${contentId} published to Spotify` });
});

// Health check endpoint
app.get('/health', (req: Request, res: Response): void => {
  console.log('Health check accessed');
  res.json({ status: 'Server running', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
