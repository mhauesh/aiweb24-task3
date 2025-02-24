import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

const HUB_AUTHKEY = "1234567890";
const HUB_URL = "http://localhost:5555";

function App() {
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [username, setUsername] = useState(() => localStorage.getItem("username") || "");
  const [isUsernameSet, setIsUsernameSet] = useState(() => !!localStorage.getItem("username"));
  const [content, setContent] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [unreadCounts, setUnreadCounts] = useState({});
  const [selectedTag, setSelectedTag] = useState("");
  const [messageTag, setMessageTag] = useState("");

  const tagOptions = ["", "urgent", "event", "offer", "request"];

  useEffect(() => {
    fetchChannels();
    const interval = setInterval(fetchChannels, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedChannel) {
      fetchMessages(selectedChannel);
      const interval = setInterval(() => updateUnreadCounts(), 5000);
      return () => clearInterval(interval);
    }
  }, [selectedChannel]);

  const fetchChannels = async () => {
    try {
      const response = await axios.get(`${HUB_URL}/channels`, {
        headers: { Authorization: `authkey ${HUB_AUTHKEY}` },
      });
      console.log("Fetched channels:", response.data);
      const fetchedChannels = response.data.channels || [];
      setChannels(fetchedChannels);
      updateUnreadCounts(fetchedChannels);
    } catch (error) {
      console.error("Error fetching channels:", error.response?.data || error.message);
    }
  };

  const fetchMessages = async (channel) => {
    try {
      const response = await axios.get(channel.endpoint, {
        headers: { Authorization: `authkey ${channel.authkey}` },
      });
      console.log("Fetched messages:", response.data);
      setMessages(response.data || []);
    } catch (error) {
      console.error("Error fetching messages:", error.response?.data || error.message);
      setMessages([]);
    }
  };

  const updateUnreadCounts = async (channelList = channels) => {
    const counts = {};
    for (const channel of channelList) {
      try {
        const response = await axios.get(channel.endpoint, {
          headers: { Authorization: `authkey ${channel.authkey}` },
        });
        counts[channel.endpoint] = response.data.length;
      } catch (error) {
        counts[channel.endpoint] = 0;
      }
    }
    setUnreadCounts(counts);
  };

  const handleSetUsername = (e) => {
    e.preventDefault();
    if (username.trim()) {
      localStorage.setItem("username", username);
      setIsUsernameSet(true);
    } else {
      alert("Please enter a valid username!");
    }
  };

  const handleResetUsername = () => {
    localStorage.removeItem("username");
    setUsername("");
    setIsUsernameSet(false);
  };

  const handlePostMessage = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      const response = await axios.post(
        selectedChannel.endpoint,
        {
          content,
          sender: username,
          timestamp: new Date().toISOString(),
          extra: messageTag || null,
          body: null,
        },
        { headers: { Authorization: `authkey ${selectedChannel.authkey}` } }
      );
      console.log("Post response:", response.data);
      setContent("");
      setMessageTag("");
      fetchMessages(selectedChannel);
    } catch (error) {
      const errorMessage = error.response?.data || error.message;
      console.error("Post error:", errorMessage);
      alert(`Failed to send message: ${errorMessage}`);
    }
  };

  const formatMessage = (text) => {
    return text
      .replace(/\[b\](.*?)\[\/b\]/g, "<strong>$1</strong>")
      .replace(/\[i\](.*?)\[\/i\]/g, "<em>$1</em>");
  };

  const filteredChannels = channels.filter((c) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pinnedMessage = messages.find((msg) => msg.extra === "pinned");
  const filteredMessages = messages.filter(
    (msg) => msg.extra !== "pinned" && (!selectedTag || msg.extra === selectedTag)
  );

  return (
    <div className="app">
      {!isUsernameSet && (
        <div className="username-modal">
          <div className="modal-content">
            <h2>Welcome to the Chat Hub!</h2>
            <p>Please enter your username:</p>
            <form onSubmit={handleSetUsername}>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Your username"
                autoFocus
              />
              <button type="submit">Join</button>
            </form>
          </div>
        </div>
      )}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>Chat Channels</h2>
          {isUsernameSet && (
            <div className="user-info">
              <span className="username-display">Logged in as: {username}</span>
              <button className="reset-btn" onClick={handleResetUsername}>
                Change Username
              </button>
            </div>
          )}
        </div>
        <input
          type="text"
          placeholder="Search channels..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <ul>
          {filteredChannels.length > 0 ? (
            filteredChannels.map((channel) => (
              <li
                key={channel.endpoint}
                onClick={() => setSelectedChannel(channel)}
                className={selectedChannel?.endpoint === channel.endpoint ? "active" : ""}
              >
                {channel.name}
                {unreadCounts[channel.endpoint] > 0 && (
                  <span className="unread">({unreadCounts[channel.endpoint]})</span>
                )}
              </li>
            ))
          ) : (
            <li>No channels available</li>
          )}
        </ul>
      </div>
      <div className="chat">
        {selectedChannel ? (
          <>
            <h2>{selectedChannel.name}</h2>
            <div className="filter-section">
              <label>Filter by Tag: </label>
              <select
                value={selectedTag}
                onChange={(e) => setSelectedTag(e.target.value)}
              >
                {tagOptions.map((tag) => (
                  <option key={tag || "none"} value={tag}>
                    {tag || "All"}
                  </option>
                ))}
              </select>
            </div>
            <div className="messages">
              {pinnedMessage && (
                <div className="message pinned">
                  <span className="sender">{pinnedMessage.sender}: </span>
                  <span dangerouslySetInnerHTML={{ __html: formatMessage(pinnedMessage.content) }} />
                  {pinnedMessage.extra && <span className="tag">[{pinnedMessage.extra}]</span>}
                  <span className="timestamp">
                    {new Date(pinnedMessage.timestamp).toLocaleString()}
                  </span>
                </div>
              )}
              {filteredMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`message ${msg.sender === username ? "sent" : "received"}`}
                >
                  <span className="sender">{msg.sender}: </span>
                  <span dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }} />
                  {msg.extra && <span className="tag">[{msg.extra}]</span>}
                  <span className="timestamp">
                    {new Date(msg.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
            <form onSubmit={handlePostMessage} className="message-form">
              <input
                type="text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Type a message... (e.g., [b]bold[/b], [i]italic[/i])"
              />
              <select
                value={messageTag}
                onChange={(e) => setMessageTag(e.target.value)}
              >
                {tagOptions.map((tag) => (
                  <option key={tag || "none"} value={tag}>
                    {tag || "No Tag"}
                  </option>
                ))}
              </select>
              <button type="submit">Send</button>
            </form>
          </>
        ) : (
          <div className="no-channel">
            <p>Select a channel to start chatting!</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;