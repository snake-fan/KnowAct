import {
  EvidenceRecord,
  KnowledgeMap,
  KnowledgeNode,
  MapEdgeConsistencyWarning
} from "../../api/authoring";

export function MapLegend() {
  return (
    <div className="map-legend" aria-label="Mastery color scale">
      {(["L0", "L1", "L2", "L3", "L4", "L5"] as const).map((level) => (
        <span key={level} className={`mastery-chip mastery-${level.toLowerCase()}`}>{level}</span>
      ))}
    </div>
  );
}

export function MapNodeInspectionCard({
  node,
  knowledgeMap,
  warnings = [],
  onClose
}: {
  node: KnowledgeNode;
  knowledgeMap: KnowledgeMap;
  warnings?: MapEdgeConsistencyWarning[];
  onClose: () => void;
}) {
  const state = knowledgeMap.states.find((candidate) => candidate.node_id === node.id);
  if (!state) return null;

  const evidenceById = new Map(knowledgeMap.evidence.map((record) => [record.id, record]));
  const evidence = state.evidence_refs.map((evidenceRef) => ({
    evidenceRef,
    record: evidenceById.get(evidenceRef) ?? null
  }));
  const nodeWarnings = warnings.filter(
    (warning) => warning.source_node_id === node.id || warning.target_node_id === node.id
  );

  return (
    <aside className="node-popover" aria-label={`Knowledge map details for ${node.name}`}>
      <div className="node-popover-header">
        <div>
          <p className="eyebrow">Knowledge Node</p>
          <h3>{node.name}</h3>
        </div>
        <button type="button" className="remove-item-button" aria-label="Close node details" onClick={onClose}>
          &#215;
        </button>
      </div>

      <section>
        <h4>Graph Node</h4>
        <MapMeta label="ID" value={node.id} />
        <MapMeta label="Type" value={node.type} />
        {node.definition && <p>{node.definition}</p>}
        {node.diagnostic_goal && <p>{node.diagnostic_goal}</p>}
        <MapPreviewList
          title="Source Locators"
          items={node.source_locators.map((locator) =>
            `${locator.source_id}: ${locator.locator}${locator.note ? ` - ${locator.note}` : ""}`
          )}
        />
        <details>
          <summary>Rubrics and diagnostic signals</summary>
          <MapPreviewList title="Diagnostic Signals" items={node.diagnostic_signals} />
          <div className="rubric-list">
            {Object.entries(node.levels).map(([level, description]) => (
              <MapMeta key={level} label={level} value={description} />
            ))}
          </div>
        </details>
      </section>

      <section>
        <h4>User Knowledge State</h4>
        <MapMeta label="Mastery Level" value={state.mastery_level} />
        <MapPreviewList title="Misconceptions" items={state.misconceptions} />
        <MapPreviewList title="Unknowns" items={state.unknowns} />
      </section>

      <section>
        <h4>Evidence Records</h4>
        {evidence.length === 0 ? (
          <p className="empty">No evidence refs.</p>
        ) : (
          <div className="evidence-list">
            {evidence.map(({ evidenceRef, record }) => (
              <EvidenceCard key={evidenceRef} evidenceRef={evidenceRef} record={record} />
            ))}
          </div>
        )}
      </section>

      {nodeWarnings.length > 0 && (
        <section>
          <h4>Consistency Warnings</h4>
          <div className="evidence-list">
            {nodeWarnings.map((warning) => (
              <article key={warning.edge_id} className="evidence-card warning">
                <strong>{warning.edge_id}</strong>
                <span>{warning.source_node_id} {warning.source_mastery_level} {" -> "} {warning.target_node_id} {warning.target_mastery_level}</span>
                <p>{warning.rule}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </aside>
  );
}

export function MapPreviewList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="preview-list">
      <strong>{title}</strong>
      <ul>
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function MapMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="profile-meta map-meta">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EvidenceCard({
  evidenceRef,
  record
}: {
  evidenceRef: string;
  record: EvidenceRecord | null;
}) {
  return (
    <article className={record ? "evidence-card" : "evidence-card missing"}>
      <strong>{evidenceRef}</strong>
      {record ? (
        <>
          <span>{record.evidence_kind} / {record.evidence_type} / {record.visibility}</span>
          <p>{record.signal}</p>
        </>
      ) : (
        <p>Missing referenced Evidence Record.</p>
      )}
    </article>
  );
}
