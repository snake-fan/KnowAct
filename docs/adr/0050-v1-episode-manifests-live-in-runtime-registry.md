# V1 episode manifests live in the runtime registry

KnowAct v1 stores **Evaluation Episode Manifests** in a **Runtime Episode Registry** instead of under individual benchmark-domain directories. The evaluation runtime owns experiment selection and orchestration across domains, while each episode manifest still binds exactly one benchmark domain, one reviewed graph version, and one hidden reviewed map.

**Considered Options**

- Store episode manifests under each benchmark domain.
- Store episode manifests in a runtime-owned registry that can select episodes across benchmark domains.

**Consequences**

Cross-domain and parallel tested-agent evaluation can be orchestrated from the runtime boundary, but episode manifests must carry explicit domain, graph-version, and map identity so reviewed artifacts remain unambiguous.
