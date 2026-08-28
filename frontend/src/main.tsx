import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyFontScale, readFontScale } from "./fontScale";
import "./styles.css";

applyFontScale(readFontScale(window.localStorage));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
