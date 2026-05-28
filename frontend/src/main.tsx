import React from "react";
import { createRoot } from "react-dom/client";
import { CandidateGraphWorkbench } from "./features/candidateGraph/CandidateGraphWorkbench";
import "./styles.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <CandidateGraphWorkbench />
  </React.StrictMode>
);
