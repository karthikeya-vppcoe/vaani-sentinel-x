'use client';
import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface ContentItem {
  id: string;
  type: 'tweet' | 'post' | 'voice_script' | 'voice';
  content?: string;
  url: string;
  timestamp: string;
}

interface ScoreItem {
  id: string;
  ethics: number;
  virality: number;
  neutrality: number;
}

interface AlertItem {
  timestamp: string;
  message: string;
}

export default function ContentPanel() {
  const [contentItems, setContentItems] = useState<ContentItem[]>([]);
  const [scores, setScores] = useState<ScoreItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'content' | 'dashboard' | 'alerts'>('content');
  const [loadingContent, setLoadingContent] = useState(true);
  const [loadingScores, setLoadingScores] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [errorContent, setErrorContent] = useState<string | null>(null);
  const [errorScores, setErrorScores] = useState<string | null>(null);
  const [errorAlerts, setErrorAlerts] = useState<string | null>(null);

  useEffect(() => {
    const fetchContent = async () => {
      setLoadingContent(true);
      setErrorContent(null);
      const token = localStorage.getItem('token');
      if (!token) {
        setErrorContent('Please log in to view content.');
        setLoadingContent(false);
        return;
      }
      try {
        const res = await fetch('http://localhost:5000/api/content', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const items: ContentItem[] = await res.json();
          setContentItems(
            items.sort((a: ContentItem, b: ContentItem) =>
              b.timestamp.localeCompare(a.timestamp)
            )
          );
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        console.error('Failed to fetch content:', err);
        setErrorContent('Failed to load content. Please try again.');
      } finally {
        setLoadingContent(false);
      }
    };

    const fetchScores = async () => {
      setLoadingScores(true);
      setErrorScores(null);
      const token = localStorage.getItem('token');
      if (!token) {
        setErrorScores('Please log in to view scores.');
        setLoadingScores(false);
        return;
      }
      try {
        const res = await fetch('http://localhost:5000/api/scores', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const scoreData: ScoreItem[] = await res.json();
          setScores(scoreData);
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        console.error('Failed to fetch scores:', err);
        setErrorScores('Failed to load scores. Please try again.');
      } finally {
        setLoadingScores(false);
      }
    };

    const fetchAlerts = async () => {
      setLoadingAlerts(true);
      setErrorAlerts(null);
      const token = localStorage.getItem('token');
      if (!token) {
        setErrorAlerts('Please log in to view alerts.');
        setLoadingAlerts(false);
        return;
      }
      try {
        const res = await fetch('http://localhost:5000/api/alerts', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const alertData: AlertItem[] = await res.json();
          setAlerts(alertData);
        } else if (res.status === 404) {
          setErrorAlerts('Alerts endpoint not found. Please ensure the server is running correctly.');
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        console.error('Failed to fetch alerts:', err);
        setErrorAlerts('Failed to load alerts. Please try again.');
      } finally {
        setLoadingAlerts(false);
      }
    };

    fetchContent();
    fetchScores();
    fetchAlerts();
  }, []);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDownload = async (url: string, filename: string) => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please log in to download files.');
      return;
    }
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(`Failed to download file: ${response.status}`);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download file');
    }
  };

  const chartData = {
    labels: scores.map((score) => `Content ${score.id}`),
    datasets: [
      {
        label: 'Ethics',
        data: scores.map((score) => score.ethics * 100),
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
      {
        label: 'Virality',
        data: scores.map((score) => score.virality * 100),
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
      {
        label: 'Neutrality',
        data: scores.map((score) => score.neutrality * 100),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
    ],
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl mb-4">AI-Generated Content</h2>
      {/* Tabs */}
      <div className="mb-4">
        <button
          onClick={() => setActiveTab('content')}
          className={`px-4 py-2 mr-2 rounded ${
            activeTab === 'content' ? 'bg-blue-500 text-white' : 'bg-gray-200'
          }`}
        >
          Content
        </button>
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`px-4 py-2 mr-2 rounded ${
            activeTab === 'dashboard' ? 'bg-blue-500 text-white' : 'bg-gray-200'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 rounded ${
            activeTab === 'alerts' ? 'bg-blue-500 text-white' : 'bg-gray-200'
          }`}
        >
          Alerts
        </button>
      </div>

      {/* Content Tab */}
      {activeTab === 'content' && (
        <div className="grid gap-4">
          {loadingContent ? (
            <p>Loading content...</p>
          ) : errorContent ? (
            <p className="text-red-500">{errorContent}</p>
          ) : contentItems.length === 0 ? (
            <p>No content available. Run the pipeline to generate content.</p>
          ) : (
            contentItems.map((item) => (
              <div key={`${item.id}-${item.type}-${item.timestamp}`} className="border p-4 rounded">
                <p>
                  <strong>Type:</strong> {item.type}
                </p>
                <p>
                  <strong>ID:</strong> {item.id}
                </p>
                <p>
                  <strong>Timestamp:</strong> {item.timestamp}
                </p>
                {item.content && (
                  <>
                    <p>
                      <strong>Content:</strong> {item.content}
                    </p>
                    <button
                      onClick={() => copyToClipboard(item.content!, `${item.id}-${item.type}`)}
                      className="bg-green-500 text-white px-4 py-2 rounded mr-2"
                    >
                      {copied === `${item.id}-${item.type}` ? 'Copied!' : 'Copy'}
                    </button>
                  </>
                )}
                {item.type === 'voice' && (
                  <audio controls className="my-2">
                    <source
                      src={`${item.url}?token=${localStorage.getItem('token')}`}
                      type="audio/mpeg"
                    />
                    Your browser does not support the audio element.
                  </audio>
                )}
                <button
                  onClick={() => handleDownload(item.url, item.url.split('/').pop() || 'download')}
                  className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                  Download
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && (
        <div className="grid gap-4">
          <h3 className="text-xl mb-2">Content Scores</h3>
          {loadingScores ? (
            <p>Loading scores...</p>
          ) : errorScores ? (
            <p className="text-red-500">{errorScores}</p>
          ) : scores.length === 0 ? (
            <p>No scores available. Run Agent D to compute scores.</p>
          ) : (
            <>
              <div className="mb-4">
                <Bar
                  data={chartData}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: { position: 'top' },
                      title: { display: true, text: 'Content Scores' },
                    },
                    scales: {
                      y: { beginAtZero: true, max: 100, title: { display: true, text: 'Score (%)' } },
                    },
                  }}
                />
              </div>
              <table className="w-full border-collapse border">
                <thead>
                  <tr>
                    <th className="border p-2">Content ID</th>
                    <th className="border p-2">Ethics Score</th>
                    <th className="border p-2">Virality Score</th>
                    <th className="border p-2">Neutrality Score</th>
                  </tr>
                </thead>
                <tbody>
                  {scores.map((score, index) => (
                    <tr key={`${score.id}-${index}`}>
                      <td className="border p-2">{score.id}</td>
                      <td className="border p-2">{(score.ethics * 100).toFixed(1)}%</td>
                      <td className="border p-2">{(score.virality * 100).toFixed(1)}%</td>
                      <td className="border p-2">{(score.neutrality * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="grid gap-4">
          <h3 className="text-xl mb-2">Security Alerts</h3>
          {loadingAlerts ? (
            <p>Loading alerts...</p>
          ) : errorAlerts ? (
            <p className="text-red-500">{errorAlerts}</p>
          ) : alerts.length === 0 ? (
            <p>No alerts found.</p>
          ) : (
            <table className="w-full border-collapse border">
              <thead>
                <tr>
                  <th className="border p-2">Timestamp</th>
                  <th className="border p-2">Alert</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert, index) => (
                  <tr key={`${alert.timestamp}-${index}`}>
                    <td className="border p-2">{alert.timestamp}</td>
                    <td className="border p-2">{alert.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
