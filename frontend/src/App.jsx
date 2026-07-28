import { useCallback, useEffect, useRef, useState } from "react";

const suggestions = [
  {
    icon: "✦",
    title: "Présente-toi",
    prompt: "Présente-toi et explique ce que tu peux faire.",
  },
  {
    icon: "↗",
    title: "Une idée de projet",
    prompt: "Donne-moi une idée de projet simple et utile à réaliser.",
  },
  {
    icon: "◎",
    title: "Explique simplement",
    prompt: "Explique-moi simplement comment fonctionne une IA.",
  },
];

function BrandMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  );
}

function Icon({ name }) {
  const paths = {
    plus: "M12 5v14M5 12h14",
    upload: "M12 16V4m0 0L7 9m5-5 5 5M5 15v4h14v-4",
    download:
      "M12 4v12m0 0 5-5m-5 5-5-5M5 20h14",
    send: "m4 4 16 8-16 8 3-8-3-8Zm3 8h13",
    file: "M7 3h7l4 4v14H7V3Zm7 0v5h5M10 13h5M10 17h5",
    close: "m6 6 12 12M18 6 6 18",
    menu: "M4 7h16M4 12h16M4 17h16",
  };
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState({
    ready: false,
    model: "qwen-local",
    loading: true,
  });
  const [settings, setSettings] = useState({
    temperature: 0.4,
    maxTokens: 256,
  });
  const [document, setDocument] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fileInputRef = useRef(null);
  const scrollAnchorRef = useRef(null);
  const abortRef = useRef(null);

  const refreshHealth = useCallback(async () => {
    try {
      const response = await fetch("/api/health");
      const payload = await response.json();
      setStatus({...payload, loading: false});
    } catch {
      setStatus({
        ready: false,
        model: "qwen-local",
        detail: "API FastAPI inaccessible",
        loading: false,
      });
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    const timer = window.setInterval(refreshHealth, 10_000);
    return () => window.clearInterval(timer);
  }, [refreshHealth]);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  const newChat = () => {
    abortRef.current?.abort();
    setMessages([]);
    setDocument(null);
    setInput("");
    setIsGenerating(false);
    setSidebarOpen(false);
  };

  const sendMessage = async (suggestedPrompt) => {
    const prompt = (suggestedPrompt ?? input).trim();
    if (!prompt || isGenerating || !status.ready) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt,
    };
    const assistantId = crypto.randomUUID();
    const conversation = [...messages, userMessage];
    setMessages([
      ...conversation,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setInput("");
    setIsGenerating(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          messages: conversation.map(({ role, content }) => ({
            role,
            content,
          })),
          temperature: settings.temperature,
          max_tokens: settings.maxTokens,
          document_content: document?.content ?? null,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Erreur HTTP ${response.status}`);
      }
      if (!response.body) throw new Error("Flux de réponse indisponible.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const chunk = JSON.parse(line);
          if (chunk.error) throw new Error(chunk.error);
          if (chunk.content) {
            fullResponse += chunk.content;
            const current = fullResponse;
            setMessages((items) =>
              items.map((item) =>
                item.id === assistantId
                  ? { ...item, content: current }
                  : item,
              ),
            );
          }
        }
        if (done) break;
      }

      if (!fullResponse.trim()) {
        throw new Error("Le modèle a renvoyé une réponse vide.");
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        setMessages((items) =>
          items.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  content: `Une erreur est survenue : ${error.message}`,
                  error: true,
                }
              : item,
          ),
        );
      }
    } finally {
      abortRef.current = null;
      setIsGenerating(false);
    }
  };

  const uploadFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    const data = new FormData();
    data.append("file", file);
    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: data,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Échec du traitement.");
      setDocument(payload);
    } catch (error) {
      setDocument({ filename: file.name, error: error.message });
    } finally {
      setUploading(false);
    }
  };

  const exportChat = () => {
    const body = messages
      .filter((message) => message.content)
      .map(
        (message) =>
          `## ${message.role === "user" ? "Vous" : "Assistant"}\n\n${message.content}`,
      )
      .join("\n\n");
    const blob = new Blob(
      [`# Conversation AZE LLM\n\n${body}\n`],
      { type: "text/markdown;charset=utf-8" },
    );
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = "conversation-aze-llm.md";
    link.click();
    URL.revokeObjectURL(url);
  };

  const onInputKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app-shell">
      <button
        className="mobile-menu"
        onClick={() => setSidebarOpen(true)}
        aria-label="Ouvrir le menu"
      >
        <Icon name="menu" />
      </button>

      {sidebarOpen && (
        <button
          className="sidebar-scrim"
          onClick={() => setSidebarOpen(false)}
          aria-label="Fermer le menu"
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="brand">
          <BrandMark />
          <div>
            <strong>AZE</strong>
            <span>LOCAL INTELLIGENCE</span>
          </div>
          <button
            className="sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Fermer le menu"
          >
            <Icon name="close" />
          </button>
        </div>

        <button className="new-chat" onClick={newChat}>
          <Icon name="plus" />
          Nouvelle conversation
        </button>

        <section className="sidebar-section document-section">
          <p className="eyebrow">CONTEXTE</p>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            accept=".txt,.md,.pdf,.docx,.mp3,.wav,.mp4,.mov"
            onChange={uploadFile}
          />
          {!document ? (
            <button
              className="upload-zone"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <span className="upload-icon">
                <Icon name="upload" />
              </span>
              <strong>{uploading ? "Traitement…" : "Ajouter un document"}</strong>
              <small>PDF, texte, audio ou vidéo</small>
            </button>
          ) : (
            <div className={`file-card ${document.error ? "has-error" : ""}`}>
              <span className="file-icon"><Icon name="file" /></span>
              <div>
                <strong>{document.filename}</strong>
                <small>
                  {document.error || (document.truncated ? "Contenu abrégé" : "Prêt à utiliser")}
                </small>
              </div>
              <button
                onClick={() => setDocument(null)}
                aria-label="Retirer le document"
              >
                <Icon name="close" />
              </button>
            </div>
          )}
        </section>

        <section className="sidebar-section settings">
          <p className="eyebrow">RÉGLAGES</p>
          <label>
            <span>
              Créativité
              <output>{settings.temperature.toFixed(1)}</output>
            </span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(event) =>
                setSettings((current) => ({
                  ...current,
                  temperature: Number(event.target.value),
                }))
              }
            />
          </label>
          <label>
            <span>
              Longueur
              <output>{settings.maxTokens}</output>
            </span>
            <input
              type="range"
              min="64"
              max="512"
              step="64"
              value={settings.maxTokens}
              onChange={(event) =>
                setSettings((current) => ({
                  ...current,
                  maxTokens: Number(event.target.value),
                }))
              }
            />
          </label>
        </section>

        <div className="sidebar-footer">
          <div className="engine-status">
            <span
              className={`status-dot ${status.ready ? "online" : ""}`}
              aria-hidden="true"
            />
            <div>
              <strong>{status.ready ? "Moteur connecté" : "Moteur indisponible"}</strong>
              <small>{status.model}</small>
            </div>
          </div>
          <button
            className="export-button"
            onClick={exportChat}
            disabled={!messages.length}
          >
            <Icon name="download" />
            Exporter
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <span className={`status-dot ${status.ready ? "online" : ""}`} />
            {status.loading
              ? "Connexion…"
              : status.ready
                ? "Qwen est prêt"
                : "Moteur hors ligne"}
          </div>
          <span>100 % local</span>
        </header>

        <div className={`conversation ${messages.length ? "has-messages" : ""}`}>
          {!messages.length ? (
            <section className="welcome">
              <div className="welcome-mark"><BrandMark /></div>
              <p className="eyebrow">ASSISTANT PERSONNEL</p>
              <h1>Que puis-je faire<br />pour vous aujourd’hui&nbsp;?</h1>
              <p className="welcome-copy">
                Une intelligence locale, privée et disponible.
                <br />Vos données restent sur cette machine.
              </p>
              <div className="suggestions">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion.title}
                    onClick={() => sendMessage(suggestion.prompt)}
                    disabled={!status.ready || isGenerating}
                  >
                    <span>{suggestion.icon}</span>
                    <strong>{suggestion.title}</strong>
                    <small>{suggestion.prompt}</small>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <section className="messages" aria-live="polite">
              {messages.map((message, index) => (
                <article
                  className={`message ${message.role} ${message.error ? "error" : ""}`}
                  key={message.id}
                >
                  <div className="message-avatar">
                    {message.role === "assistant" ? <BrandMark /> : "VOUS"}
                  </div>
                  <div className="message-content">
                    <p className="message-label">
                      {message.role === "assistant" ? "AZE" : "Vous"}
                    </p>
                    {message.content ? (
                      <div className="message-text">{message.content}</div>
                    ) : index === messages.length - 1 && isGenerating ? (
                      <div className="thinking">
                        <span />
                        <span />
                        <span />
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
              <div ref={scrollAnchorRef} />
            </section>
          )}
        </div>

        <footer className="composer-wrap">
          {document && !document.error && (
            <div className="composer-file">
              <Icon name="file" />
              <span>{document.filename}</span>
              <button onClick={() => setDocument(null)} aria-label="Retirer">
                <Icon name="close" />
              </button>
            </div>
          )}
          <div className="composer">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={onInputKeyDown}
              rows="1"
              placeholder={
                status.ready
                  ? "Écrivez votre message…"
                  : "Démarrez llama-server pour discuter"
              }
              disabled={!status.ready || isGenerating}
              aria-label="Votre message"
            />
            <button
              className="send-button"
              onClick={() => sendMessage()}
              disabled={!input.trim() || !status.ready || isGenerating}
              aria-label="Envoyer"
            >
              <Icon name="send" />
            </button>
          </div>
          <p>
            AZE peut faire des erreurs. Vérifiez les informations importantes.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
