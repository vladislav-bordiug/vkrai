import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = {
  async sendChat(payload) {
    const res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async getSessionsByEmail(email) {
    const res = await fetch(`${API_BASE_URL}/api/users/sessions?email=${encodeURIComponent(email)}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async getSessionMessages(sessionId) {
    const res = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

export function App() {
  const [userName, setUserName] = useState("Local User");
  const [userEmail, setUserEmail] = useState("local@example.com");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState("");
  const [messageToolTraces, setMessageToolTraces] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const canLoadSessions = useMemo(() => userEmail.trim().length > 3, [userEmail]);

  const hydrateSessionData = (rawMessages) => {
    const visibleMessages = [];
    const traces = [];
    let lastAssistantIndex = -1;

    for (const msg of rawMessages || []) {
      if (msg.role === "assistant") {
        visibleMessages.push(msg);
        traces.push([]);
        lastAssistantIndex += 1;
        continue;
      }

      if (msg.role === "tool") {
        if (lastAssistantIndex >= 0) {
          try {
            traces[lastAssistantIndex].push(JSON.parse(msg.content));
          } catch {
            traces[lastAssistantIndex].push({ raw: msg.content });
          }
        }
        continue;
      }

      if (msg.role === "user") {
        visibleMessages.push(msg);
      }
    }

    setMessages(visibleMessages);
    setMessageToolTraces(traces);
  };

  const openSession = async (sessionId) => {
    setError("");
    setActiveSessionId(sessionId);
    try {
      const data = await api.getSessionMessages(sessionId);
      hydrateSessionData(data);
    } catch (e) {
      setError(`Ошибка загрузки сообщений: ${e.message}`);
    }
  };

  const loadSessions = async () => {
    if (!canLoadSessions) return;
    setError("");
    try {
      const data = await api.getSessionsByEmail(userEmail.trim());
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        await openSession(data[0].id);
      }
    } catch (e) {
      setError(`Ошибка загрузки сессий: ${e.message}`);
    }
  };

  const createNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setMessageToolTraces([]);
    setError("");
  };

  const submitMessage = async (e) => {
    e.preventDefault();
    const text = messageInput.trim();
    if (!text || isLoading) return;

    setIsLoading(true);
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setMessageInput("");

    try {
      const result = await api.sendChat({
        user_name: userName.trim() || "Local User",
        user_email: userEmail.trim() || "local@example.com",
        session_id: activeSessionId,
        message: text,
      });

      setActiveSessionId(result.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
      setMessageToolTraces((prev) => [...prev, result.tool_trace || []]);
      await loadSessions();
    } catch (e) {
      setError(`Ошибка отправки: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="app">
      <header className="topbar card">
        <h1>Локальный ИИ-ассистент</h1>
        <p>История чатов, продолжение сессий, tool trace по каждому ответу</p>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <section className="card">
            <h2>Пользователь</h2>
            <div className="row">
              <label htmlFor="userName">Имя</label>
              <input id="userName" value={userName} onChange={(e) => setUserName(e.target.value)} />
            </div>
            <div className="row">
              <label htmlFor="userEmail">Email</label>
              <input id="userEmail" type="email" value={userEmail} onChange={(e) => setUserEmail(e.target.value)} />
            </div>
            <div className="actions">
              <button onClick={loadSessions} type="button">
                Обновить сессии
              </button>
              <button onClick={createNewChat} type="button">
                Новый чат
              </button>
            </div>
          </section>

          <section className="card">
            <h2>История чатов</h2>
            <div className="session-list">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  className={`session-item ${activeSessionId === s.id ? "active" : ""}`}
                  onClick={() => openSession(s.id)}
                  type="button"
                >
                  <div>{s.title || "Без названия"}</div>
                  <small>{new Date(s.created_at).toLocaleString("ru-RU")}</small>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="chat-shell">
          <section className="chat card">
            <h2>{activeSessionId ? "Продолжение чата" : "Новый чат"}</h2>
            <div className="messages">
              {(() => {
                let assistantIndex = -1;
                return messages.map((m, idx) => {
                  const isAssistant = m.role === "assistant";
                  if (isAssistant) assistantIndex += 1;
                  const trace = isAssistant ? messageToolTraces[assistantIndex] || [] : [];

                  return (
                    <div key={`${idx}-${m.role}`} className={`message ${m.role}`}>
                      {m.role === "user" ? "Вы" : "Ассистент"}: {m.content}
                      {isAssistant && trace.length > 0 ? (
                        <details style={{ marginTop: 8 }}>
                          <summary>Вызовы тулов ({trace.length})</summary>
                          <pre>{JSON.stringify(trace, null, 2)}</pre>
                        </details>
                      ) : null}
                    </div>
                  );
                });
              })()}
            </div>
            <form className="composer" onSubmit={submitMessage}>
              <textarea
                rows={3}
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                placeholder="Например: Покажи погоду в Москве и мои задачи Todoist"
              />
              <button type="submit" disabled={isLoading}>
                {isLoading ? "Отправка..." : "Отправить"}
              </button>
            </form>
          </section>

        </section>
      </div>

      {error ? (
        <section className="card">
          <strong>Ошибка</strong>
          <p>{error}</p>
        </section>
      ) : null}
    </main>
  );
}

