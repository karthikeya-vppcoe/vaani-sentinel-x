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
const ALERTS_PATH = path.resolve(__dirname, '../../../logs/alert_dashboard.json');
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
    // Only use finalized content from content_ready
    const currentDir = CONTENT_DIR;
    const groupedContent: Record<string, any[]> = {};
    console.log('Fetching content from:', currentDir);
    try {
      await fs.access(currentDir);
      // Get language directories
      const langDirs = await fs.readdir(currentDir);
      console.log('Language directories found:', langDirs);
      // Process each language directory
      for (const langDir of langDirs) {
        const langPath = path.join(currentDir, langDir);
        const langStat = await fs.stat(langPath);
        // Skip if not a directory
        if (!langStat.isDirectory()) continue;
        // Get files in the language directory
        const files = await fs.readdir(langPath);
        console.log(`Files found in ${langDir}:`, files);
        for (const file of files) {
          const filePath = path.join(langPath, file);
          // Process JSON files to extract metadata
          if (file.endsWith('.json')) {
            try {
              const fileContent = await fs.readFile(filePath, 'utf-8');
              const jsonContent = JSON.parse(fileContent);
              let content: string | undefined;
              let contentType: string;
              let sentiment: string = jsonContent.sentiment || 'neutral';
              let language: string = jsonContent.language || langDir;
              if (jsonContent.text) {
                content = jsonContent.text;
                contentType = jsonContent.type || 'post';
              } else if (jsonContent.post) {
                content = jsonContent.post;
                contentType = 'post';
              } else if (jsonContent.tweet) {
                content = jsonContent.tweet;
                contentType = 'tweet';
              } else if (jsonContent.voice_script) {
                content = jsonContent.voice_script;
                contentType = 'voice_script';
              } else {
                continue;
              }
              const id = jsonContent.id || file.split('.')[0];
              const item = {
                id,
                type: contentType,
                content,
                url: `http://localhost:${PORT}/content/${langDir}/${file}`,
                timestamp: new Date().toISOString(),
                language,
                sentiment
              };
              if (!groupedContent[language]) groupedContent[language] = [];
              groupedContent[language].push(item);
            } catch (jsonError) {
              console.error(`Error processing JSON file ${file}:`, jsonError);
            }
          } else if (file.endsWith('.mp3')) {
            const parts = file.split(/[_|.]/);
            if (parts.length < 2) continue;
            const id = parts[1] || file.split('.')[0];
            const item = {
              id,
              type: 'voice',
              url: `http://localhost:${PORT}/content/${langDir}/${file}`,
              timestamp: new Date().toISOString(),
              language: langDir,
              sentiment: 'neutral'
            };
            if (!groupedContent[langDir]) groupedContent[langDir] = [];
            groupedContent[langDir].push(item);
          }
        }
      }
    } catch (accessError) {
      console.warn('content_ready directory not found, returning empty content');
      res.status(200).json(groupedContent);
      return;
    }
    console.log('Grouped content items to return:', groupedContent);
    res.json(groupedContent);
  } catch (error) {
    console.error('Error in /api/content:', error);
    res.status(500).json({ message: 'Failed to load content', error: (error as Error).message });
  }
});

// New endpoint for sentiment content from multilingual_ready
app.get('/api/sentiment-content', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    const sentimentDir = path.resolve(__dirname, '../../../content/multilingual_ready');
    const sentimentItems: any[] = [];
    console.log('Fetching sentiment content from:', sentimentDir);
    try {
      await fs.access(sentimentDir);
      // Get language directories
      const langDirs = await fs.readdir(sentimentDir);
      console.log('Language directories found:', langDirs);
      // Process each language directory
      for (const langDir of langDirs) {
        const langPath = path.join(sentimentDir, langDir);
        const langStat = await fs.stat(langPath);
        // Skip if not a directory
        if (!langStat.isDirectory()) continue;
        // Get files in the language directory
        const files = await fs.readdir(langPath);
        console.log(`Files found in ${langDir}:`, files);
        if (files.length === 0) {
          console.log(`No files found in ${langDir}, skipping...`);
          continue;
        }
        for (const file of files) {
          const filePath = path.join(langPath, file);
          if (file.endsWith('.json')) {
            try {
              const fileContent = await fs.readFile(filePath, 'utf-8');
              const jsonContent = JSON.parse(fileContent);
              let content: string | undefined;
              let contentType: string;
              let sentiment: string = jsonContent.sentiment || 'neutral';
              let language: string = jsonContent.language || langDir;
              if (jsonContent.text) {
                content = jsonContent.text;
                contentType = jsonContent.type || 'fact';
              } else if (jsonContent.fact) {
                content = jsonContent.fact;
                contentType = 'fact';
              } else if (jsonContent.quote) {
                content = jsonContent.quote;
                contentType = 'quote';
              } else if (jsonContent['micro-article']) {
                content = jsonContent['micro-article'];
                contentType = 'micro-article';
              } else {
                console.log(`Skipping file ${file}: No recognized content field`);
                continue;
              }
              const id = jsonContent.id || file.split('.')[0];
              sentimentItems.push({
                id,
                type: contentType,
                content,
                url: `http://localhost:${PORT}/content/${langDir}/${file}`,
                timestamp: new Date().toISOString(),
                language,
                sentiment
              });
            } catch (jsonError) {
              console.error(`Error processing JSON file ${file}:`, jsonError);
            }
          } else {
            console.log(`Skipping non-JSON file: ${file}`);
          }
        }
      }
    } catch (accessError) {
      console.warn('multilingual_ready directory not found, returning empty sentiment content');
      res.status(200).json(sentimentItems);
      return;
    }
    if (sentimentItems.length === 0) {
      console.log('No sentiment items found in multilingual_ready');
    }
    console.log('Sentiment content items to return:', sentimentItems);
    res.json(sentimentItems);
  } catch (error) {
    console.error('Error in /api/sentiment-content:', error);
    res.status(500).json({ message: 'Failed to load sentiment content', error: (error as Error).message });
  }
});

// Serve content files
app.get('/content/:lang/:filename', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  const { lang, filename } = req.params;
  
  // Try to find the file in both content directories
  const contentDirs = [
    CONTENT_DIR,
    path.resolve(__dirname, '../../../content/multilingual_ready')
  ];
  
  let fileFound = false;
  
  for (const dir of contentDirs) {
    const filePath = path.join(dir, lang, filename);
    console.log('Trying to serve file from:', filePath);
    
    try {
      await fs.access(filePath);
      res.sendFile(filePath, {
        headers: {
          'Content-Type': filePath.endsWith('.mp3') ? 'audio/mpeg' : 'application/json',
        },
      });
      fileFound = true;
      console.log('File served successfully from:', filePath);
      break;
    } catch (error) {
      console.log(`File not found in ${dir}, trying next directory if available`);
    }
  }
  
  if (!fileFound) {
    console.error('Error: File not found in any content directory');
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

// Fetch alerts from alert_dashboard.json
app.get('/api/alerts', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    console.log('Fetching alerts from:', ALERTS_PATH);
    try {
      await fs.access(ALERTS_PATH);
      const alerts = JSON.parse(await fs.readFile(ALERTS_PATH, 'utf-8'));
      console.log('Alerts loaded:', alerts);
      res.json(alerts);
    } catch (accessError) {
      console.warn('alert_dashboard.json not found, returning empty alerts');
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