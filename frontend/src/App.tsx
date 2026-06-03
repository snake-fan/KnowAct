import { useState } from "react";
import { CandidateGraphWorkbench } from "./features/candidateGraph/CandidateGraphWorkbench";
import { MapAuthoringWorkbench } from "./features/mapAuthoring/MapAuthoringWorkbench";
import { UserProfileWorkbench } from "./features/userProfile/UserProfileWorkbench";

type WorkbenchModule = "knowledge-graph" | "user-profile" | "user-map";

export function App() {
  const [activeModule, setActiveModule] = useState<WorkbenchModule>("knowledge-graph");

  return (
    <div className="workbench-frame">
      <aside className="global-sidebar">
        <div className="brand-block">
          <span className="brand-mark">K</span>
          <div>
            <strong>KnowAct</strong>
            <span>Research Workbench</span>
          </div>
        </div>

        <nav className="module-nav" aria-label="Workbench modules">
          <p>Authoring</p>
          <button
            type="button"
            className={activeModule === "knowledge-graph" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("knowledge-graph")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#9672;</span>
            <span>
              <strong>Knowledge Graph</strong>
              <small>Nodes, edges, promotion</small>
            </span>
          </button>
          <button
            type="button"
            className={activeModule === "user-profile" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("user-profile")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#9786;</span>
            <span>
              <strong>User Profile</strong>
              <small>Context draft, confirmation</small>
            </span>
          </button>
          <button
            type="button"
            className={activeModule === "user-map" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("user-map")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#9638;</span>
            <span>
              <strong>User Map</strong>
              <small>Generate, review, publish</small>
            </span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <span>V1 Authoring</span>
          <p>Review gates stay explicit and reproducible.</p>
        </div>
      </aside>

      <div className="module-surface">
        <div className={activeModule === "knowledge-graph" ? "module-pane active" : "module-pane"}>
          <CandidateGraphWorkbench />
        </div>
        <div className={activeModule === "user-profile" ? "module-pane active" : "module-pane"}>
          <UserProfileWorkbench />
        </div>
        <div className={activeModule === "user-map" ? "module-pane active" : "module-pane"}>
          <MapAuthoringWorkbench />
        </div>
      </div>
    </div>
  );
}
