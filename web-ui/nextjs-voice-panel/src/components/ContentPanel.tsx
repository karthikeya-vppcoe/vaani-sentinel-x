import { useState, useEffect } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

// Fixed WarningIcon with proper sizing
const WarningIcon = () => (
  <svg
    className="w-5 h-5 text-red-500 mr-2 flex-shrink-0"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
    />
  </svg>
);

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface ContentItem {
  id: string;
  type: "tweet" | "post" | "voice_script" | "voice";
  content?: string;
  url: string;
  timestamp: string;
  language: string;
  sentiment: string;
}

interface SentimentItem {
  id: string;
  type: "fact" | "quote" | "micro-article";
  content?: string;
  url: string;
  timestamp: string;
  language: string;
  sentiment: string;
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
  const [sentimentItems, setSentimentItems] = useState<SentimentItem[]>([]);
  const [scores, setScores] = useState<ScoreItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "content" | "dashboard" | "alerts" | "sentiment"
  >("content");

  const [loadingContent, setLoadingContent] = useState(true);
  const [loadingSentiment, setLoadingSentiment] = useState(true);
  const [loadingScores, setLoadingScores] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [errorContent, setErrorContent] = useState<string | null>(null);
  const [errorSentiment, setErrorSentiment] = useState<string | null>(null);
  const [errorScores, setErrorScores] = useState<string | null>(null);
  const [errorAlerts, setErrorAlerts] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    const fetchContent = async () => {
      if (!token) {
        setErrorContent("Please log in to view content.");
        setLoadingContent(false);
        return;
      }
      try {
        const res = await fetch("http://localhost:5000/api/content", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const groupedItems: Record<string, ContentItem[]> = await res.json();
          const items = Object.entries(groupedItems)
            .filter(([lang]) => ["en", "hi", "sa"].includes(lang))
            .flatMap(([, items]) => items)
            .sort((a, b) => b.timestamp.localeCompare(a.timestamp));
          setContentItems(items);
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        setErrorContent("Failed to load content. Please try again.");
        console.error(err);
      } finally {
        setLoadingContent(false);
      }
    };

    const fetchSentimentContent = async () => {
      if (!token) {
        setErrorSentiment("Please log in to view sentiment content.");
        setLoadingSentiment(false);
        return;
      }
      try {
        const res = await fetch("http://localhost:5000/api/sentiment-content", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const items: SentimentItem[] = await res.json();
          const filteredItems = items
            .filter((item) => ["en", "hi", "sa"].includes(item.language))
            .sort((a, b) => b.timestamp.localeCompare(a.timestamp));
          setSentimentItems(filteredItems);
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        setErrorSentiment("Failed to load sentiment content. Please try again.");
        console.error(err);
      } finally {
        setLoadingSentiment(false);
      }
    };

    const fetchScores = async () => {
      if (!token) {
        setErrorScores("Please log in to view scores.");
        setLoadingScores(false);
        return;
      }
      try {
        const res = await fetch("http://localhost:5000/api/scores", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const scoreData: ScoreItem[] = await res.json();
          setScores(scoreData);
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        setErrorScores("Failed to load scores. Please try again.");
        console.error(err);
      } finally {
        setLoadingScores(false);
      }
    };

    const fetchAlerts = async () => {
      if (!token) {
        setErrorAlerts("Please log in to view alerts.");
        setLoadingAlerts(false);
        return;
      }
      try {
        const res = await fetch("http://localhost:5000/api/alerts", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const alertData: AlertItem[] = await res.json();
          setAlerts(alertData);
        } else if (res.status === 404) {
          setErrorAlerts("Alerts endpoint not found.");
        } else {
          throw new Error(`HTTP error: ${res.status}`);
        }
      } catch (err) {
        setErrorAlerts("Failed to load alerts. Please try again.");
        console.error(err);
      } finally {
        setLoadingAlerts(false);
      }
    };

    fetchContent();
    fetchSentimentContent();
    fetchScores();
    fetchAlerts();
  }, []);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDownload = async (url: string, filename: string) => {
    const token = localStorage.getItem("token");
    if (!token) {
      alert("Please log in to download files.");
      return;
    }
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(`Failed: ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Download failed:", err);
      alert("Failed to download file.");
    }
  };

  const clearAlerts = () => {
    setAlerts([]);
  };

  const chartData = {
    labels: scores.map((score) => `Content ${score.id}`),
    datasets: [
      {
        label: "Ethics",
        data: scores.map((s) => s.ethics * 100),
        backgroundColor: "rgba(75, 192, 192, 0.5)",
      },
      {
        label: "Virality",
        data: scores.map((s) => s.virality * 100),
        backgroundColor: "rgba(255, 99, 132, 0.5)",
      },
      {
        label: "Neutrality",
        data: scores.map((s) => s.neutrality * 100),
        backgroundColor: "rgba(54, 162, 235, 0.5)",
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "Content Scores",
        font: { size: 16 },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        title: {
          display: true,
          text: "Score (%)",
        },
      },
    },
  };

  // Group content items by language
  const groupedContentItems = contentItems.reduce(
    (acc: Record<string, ContentItem[]>, item: ContentItem) => {
      const lang = item.language || "unknown";
      if (!acc[lang]) acc[lang] = [];
      acc[lang].push(item);
      return acc;
    },
    {}
  );

  // Group sentiment items by language
  const groupedSentimentItems = sentimentItems.reduce(
    (acc: Record<string, SentimentItem[]>, item: SentimentItem) => {
      const lang = item.language || "unknown";
      if (!acc[lang]) acc[lang] = [];
      acc[lang].push(item);
      return acc;
    },
    {}
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-gray-200 p-6">
      <h2 className="text-3xl font-bold text-gray-800 mb-8 text-center">
        AI-Generated Content Dashboard
      </h2>

      {/* Tabs */}
      <div className="flex justify-center mb-8 border-b border-gray-200">
        {["content", "dashboard", "alerts", "sentiment"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`px-6 py-3 text-sm font-medium transition-colors duration-300 relative ${
              activeTab === tab
                ? "text-indigo-600 border-b-2 border-indigo-600"
                : "text-gray-600 hover:text-indigo-500"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {activeTab === tab && (
              <span className="absolute inset-x-0 bottom-0 h-0.5 bg-indigo-600 transform scale-x-100 transition-transform duration-300" />
            )}
          </button>
        ))}
      </div>

      {/* Loading Spinner Component */}
      {[
        loadingContent && activeTab === "content",
        loadingScores && activeTab === "dashboard",
        loadingAlerts && activeTab === "alerts",
        loadingSentiment && activeTab === "sentiment",
      ].some(Boolean) && (
        <div className="flex justify-center items-center py-8">
          <svg
            className="animate-spin h-8 w-8 text-indigo-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8h8a8 8 0 01-8 8 8 8 0 01-8-8z"
            />
          </svg>
        </div>
      )}

      {/* Content Tab */}
      {activeTab === "content" && !loadingContent && (
        <div className="animate-fade-in">
          {errorContent ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
              {errorContent}
            </div>
          ) : contentItems.length === 0 ? (
            <div className="bg-gray-50 text-gray-600 p-4 rounded-lg text-center">
              No content available. Run the pipeline to generate content.
            </div>
          ) : (
            Object.entries(groupedContentItems).map(([lang, items]) => (
              <div key={lang} className="mb-12">
                <h3 className="text-xl font-semibold text-gray-800 mb-6 capitalize">
                  Language: {lang}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {items.map((item, idx) => (
                    <div
                      key={`${item.id}-${item.type}-${item.timestamp}-${idx}`}
                      className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
                    >
                      <div className="flex justify-between items-center mb-4">
                        <p className="text-sm font-medium text-gray-700">
                          <strong>Type:</strong> {item.type}
                        </p>
                        <div className="flex gap-2">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              item.language === "en"
                                ? "bg-blue-100 text-blue-800"
                                : item.language === "hi"
                                ? "bg-green-100 text-green-800"
                                : item.language === "sa"
                                ? "bg-purple-100 text-purple-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {item.language || "en"}
                          </span>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              item.sentiment === "positive"
                                ? "bg-green-100 text-green-800"
                                : item.sentiment === "negative"
                                ? "bg-red-100 text-red-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {item.sentiment || "neutral"}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>ID:</strong> {item.id}
                      </p>
                      <p className="text-sm text-gray-600 mb-4">
                        <strong>Timestamp:</strong>{" "}
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                      {item.content && (
                        <>
                          <p className="text-gray-800 mb-4 line-clamp-3">
                            <strong>Content:</strong> {item.content}
                          </p>
                          <button
                            onClick={() =>
                              copyToClipboard(
                                item.content!,
                                `${item.id}-${item.type}`
                              )
                            }
                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition duration-200 mr-2"
                          >
                            {copied === `${item.id}-${item.type}`
                              ? "Copied!"
                              : "Copy"}
                          </button>
                        </>
                      )}
                      {item.type === "voice" && (
                        <audio controls className="my-4 w-full">
                          <source
                            src={`${item.url}?token=${localStorage.getItem(
                              "token"
                            )}`}
                            type="audio/mpeg"
                          />
                          Your browser does not support the audio element.
                        </audio>
                      )}
                      <button
                        onClick={() =>
                          handleDownload(
                            item.url,
                            item.url.split("/").pop() || "download"
                          )
                        }
                        className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-200"
                      >
                        Download
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Dashboard Tab */}
      {activeTab === "dashboard" && !loadingScores && (
        <div className="animate-fade-in">
          {errorScores ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
              {errorScores}
            </div>
          ) : scores.length === 0 ? (
            <div className="bg-gray-50 text-gray-600 p-4 rounded-lg text-center">
              No scores available.
            </div>
          ) : (
            <div className="bg-white p-6 rounded-xl shadow-md max-w-4xl mx-auto">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                Content Scores
              </h3>
              <div className="h-96">
                <Bar data={chartData} options={chartOptions} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === "alerts" && !loadingAlerts && (
        <div className="animate-fade-in">
          {errorAlerts ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
              {errorAlerts}
            </div>
          ) : alerts.length === 0 ? (
            <div className="bg-gray-50 text-gray-600 p-4 rounded-lg text-center">
              No alerts available.
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-gray-800">Alerts</h3>
                <button
                  onClick={clearAlerts}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition duration-200"
                >
                  Clear Alerts
                </button>
              </div>
              <div className="space-y-4">
                {alerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className="flex items-start p-4 bg-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
                  >
                    <WarningIcon />
                    <div className="flex-1">
                      <p className="text-sm text-gray-500 mb-1">
                        <strong>{new Date(alert.timestamp).toLocaleString()}</strong>
                      </p>
                      <p className="text-gray-800">{alert.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sentiment Metadata Tab */}
      {activeTab === "sentiment" && !loadingSentiment && (
        <div className="animate-fade-in mt-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">
            Sentiment Metadata
          </h2>
          {errorSentiment ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
              {errorSentiment}
            </div>
          ) : sentimentItems.length === 0 ? (
            <div className="bg-gray-50 text-gray-600 p-4 rounded-lg text-center">
              No sentiment metadata available.
            </div>
          ) : (
            Object.entries(groupedSentimentItems).map(([lang, items]) => (
              <div key={lang} className="mb-12">
                <h3 className="text-xl font-semibold text-gray-800 mb-6 capitalize">
                  Language: {lang}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {items.map((item, idx) => (
                    <div
                      key={`sentiment-${item.id}-${item.type}-${item.timestamp}-${idx}`}
                      className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
                    >
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>Type:</strong> {item.type}
                      </p>
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>ID:</strong> {item.id}
                      </p>
                      <p className="text-sm text-gray-600 mb-4">
                        <strong>Timestamp:</strong>{" "}
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                      <div className="flex gap-2 mb-4">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            item.language === "en"
                              ? "bg-blue-100 text-blue-800"
                              : item.language === "hi"
                              ? "bg-green-100 text-green-800"
                              : item.language === "sa"
                              ? "bg-purple-100 text-purple-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {item.language || "en"}
                        </span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            item.sentiment === "positive"
                              ? "bg-green-100 text-green-800"
                              : item.sentiment === "negative"
                              ? "bg-red-100 text-red-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {item.sentiment || "neutral"}
                        </span>
                      </div>
                      {item.content && (
                        <p className="text-gray-800 line-clamp-3">
                          <strong>Snippet:</strong>{" "}
                          {item.content.length > 100
                            ? `${item.content.substring(0, 100)}...`
                            : item.content}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}