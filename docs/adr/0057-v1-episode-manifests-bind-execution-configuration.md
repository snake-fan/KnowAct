# V1 Episode manifests bind execution configuration

KnowAct v1 selects and resolves **Episode Execution Configuration** during **Episode Manifest Registration** and stores it immutably with the **Evaluation Episode Manifest**. The configuration contains `agent_kind`, `tested_agent_client_provider`, `tested_agent_model`, `simulator_client_provider`, `simulator_model`, `tested_agent_temperature`, and `max_tool_retries`.

Registration resolves and snapshots the non-secret model names for the selected providers. Episode execution and checkpoint resume pass those pinned model names to provider adapters instead of re-reading environment model defaults. API keys, base URLs, and other credentials remain environment configuration and are never written to episode manifests.

The `Episodes` workbench renders provider-scoped model selectors from a backend **Episode Model Catalog**. Model names are not free-text inputs. Registration validates that both selected models are catalog entries for their providers before publishing the immutable manifest.

The catalog API returns only provider names, allowlisted model names, provider-scoped defaults, and availability. A provider without configured credentials is disabled in the workbench and rejected by registration, preventing creation of an episode that cannot start under the current backend configuration. API keys, base URLs, and other sensitive connection details are never returned.

Episode manifests created before this decision do not receive inferred execution configuration. They remain visible as read-only legacy artifacts in the `Episodes` workbench with a configuration-missing warning, but they are excluded from `Run Queue` and have no **Episode Execution Status**. Historical runs are not used to guess one immutable configuration or one canonical completed result. Users register a new episode under the current schema instead.

The `Episodes` workbench owns these controls together with graph, hidden map, and turn-budget selection. `Run Queue` does not expose agent or provider configuration and its enqueue request contains episode ids only. First execution, checkpoint resume, and explicit **Episode Run Restart** all use the values registered on the episode. Changing any execution setting requires registering a new `episode_id`.

**Considered Options**

- Keep agent and provider settings as mutable parameters on each run request.
- Set one shared configuration on each multi-episode enqueue command.
- Treat a registered episode as a one-shot reproducible experiment unit that binds execution configuration before entering the queue.

**Consequences**

Episode rows are self-contained and can be enqueued or resumed without queue-time configuration ambiguity. Pinning model names prevents an environment-default change from switching models inside one resumed run. Completed results remain directly attributable to the registered episode definition. The manifest and registration API become wider, and running the same graph/map setup with another agent, provider, or model requires a new episode identity. Legacy manifests remain inspectable but require explicit recreation instead of a lossy automatic migration.
