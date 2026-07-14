import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// Nudge the browser to fetch the mono display font up front. With display=swap
// the fetch is otherwise lazy and the tabular figures can linger on a system
// monospace fallback; loading the key weights explicitly makes it deterministic.
if (document.fonts) {
  ["500 1em 'Fira Code'", "700 1em 'Fira Code'", "800 1em 'Fira Sans'"].forEach(
    (f) => document.fonts.load(f).catch(() => {})
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
