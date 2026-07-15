import { Suspense, lazy, useState } from "react";

type WorkbenchModule = "knowledge-graph" | "user-profile" | "user-map" | "simulator" | "episodes" | "run-queue";

const CandidateGraphWorkbench = lazy(() =>
  import("./features/candidateGraph/CandidateGraphWorkbench").then((module) => ({
    default: module.CandidateGraphWorkbench
  }))
);
const UserProfileWorkbench = lazy(() =>
  import("./features/userProfile/UserProfileWorkbench").then((module) => ({
    default: module.UserProfileWorkbench
  }))
);
const MapAuthoringWorkbench = lazy(() =>
  import("./features/mapAuthoring/MapAuthoringWorkbench").then((module) => ({
    default: module.MapAuthoringWorkbench
  }))
);
const SimulatorWorkbench = lazy(() =>
  import("./features/simulator/SimulatorWorkbench").then((module) => ({
    default: module.SimulatorWorkbench
  }))
);
const EpisodesWorkbench = lazy(() =>
  import("./features/episodes/EpisodesWorkbench").then((module) => ({
    default: module.EpisodesWorkbench
  }))
);
const RunQueueWorkbench = lazy(() =>
  import("./features/runQueue/RunQueueWorkbench").then((module) => ({
    default: module.RunQueueWorkbench
  }))
);

const WORKBENCH_COMPONENTS = {
  "knowledge-graph": CandidateGraphWorkbench,
  "user-profile": UserProfileWorkbench,
  "user-map": MapAuthoringWorkbench,
  simulator: SimulatorWorkbench,
  episodes: EpisodesWorkbench,
  "run-queue": RunQueueWorkbench
};

export function App() {
  const [activeModule, setActiveModule] = useState<WorkbenchModule>("knowledge-graph");
  const ActiveWorkbench = WORKBENCH_COMPONENTS[activeModule];

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
          <p>Runtime</p>
          <button
            type="button"
            className={activeModule === "simulator" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("simulator")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#9655;</span>
            <span>
              <strong>Simulator</strong>
              <small>Single-turn answers</small>
            </span>
          </button>
          <button
            type="button"
            className={activeModule === "episodes" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("episodes")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#9635;</span>
            <span>
              <strong>Episodes</strong>
              <small>Immutable manifests</small>
            </span>
          </button>
          <button
            type="button"
            className={activeModule === "run-queue" ? "module-nav-item active" : "module-nav-item"}
            onClick={() => setActiveModule("run-queue")}
          >
            <span className="module-nav-icon" aria-hidden="true">&#8644;</span>
            <span>
              <strong>Run Queue</strong>
              <small>Parallel episode execution</small>
            </span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <span>V1 Authoring</span>
          <p>Review gates stay explicit and reproducible.</p>
        </div>
      </aside>

      <div className="module-surface">
        <div className="module-pane active">
          <Suspense fallback={<div className="module-loading">Loading...</div>}>
            <ActiveWorkbench />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
