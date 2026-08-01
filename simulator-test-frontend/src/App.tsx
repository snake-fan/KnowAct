import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  type CandidateMapResponse,
  type CandidateProfileContext,
  type ConfirmedProfileContext,
  type KnowledgeNode,
  type MasteryLevel,
  type ParticipantMapStateRevision,
  type ProfileContextCandidateResponse,
  type SimulatorExperimentQuestionBankSummary,
  type SimulatorExperimentSession,
  type SimulatorSelfEvaluation,
  confirmProfileContextCandidate,
  confirmParticipantMap,
  completeSimulatorExperimentSession,
  createSimulatorExperimentSession,
  generateCandidateMap,
  generateProfileContextCandidate,
  listReviewedGraphs,
  listSimulatorExperimentQuestionBanks,
  readBenchmarkDomains,
  readReviewedGraph,
  readSimulatorExperimentSession,
  saveProfileContextCandidate,
  saveSimulatorExperimentSelfEvaluation,
  submitSimulatorExperimentHumanAnswer
} from "./api";
import {
  sessionStorageKey,
  studyConfig,
  type SimulatorExperimentLanguage
} from "./config";

const MASTERY_LEVELS: MasteryLevel[] = ["L0", "L1", "L2", "L3", "L4", "L5"];

const DEFAULT_EVALUATION: SimulatorSelfEvaluation = {
  content_similarity: 3,
  knowledge_level_similarity: 3,
  boundary_similarity: 3,
  style_similarity: 3,
  overall_representativeness: 3,
  replacement_judgement: "minor_bias",
  comment: ""
};

type StudyMaterials = {
  benchmarkDomain: string;
  graphVersion: string;
  questionBank: SimulatorExperimentQuestionBankSummary;
};

export function App() {
  const [studyMaterials, setStudyMaterials] = useState<StudyMaterials | null>(null);
  const [domainSummary, setDomainSummary] = useState("");
  const [participantCode, setParticipantCode] = useState("");
  const [userId, setUserId] = useState("");
  const [mapId, setMapId] = useState("");

  const [roughDescription, setRoughDescription] = useState("");
  const [profileCandidate, setProfileCandidate] =
    useState<ProfileContextCandidateResponse | null>(null);
  const [profileDraft, setProfileDraft] =
    useState<CandidateProfileContext | null>(null);
  const [confirmedProfile, setConfirmedProfile] =
    useState<ConfirmedProfileContext | null>(null);

  const [graphNodes, setGraphNodes] = useState<KnowledgeNode[]>([]);
  const [mapCandidate, setMapCandidate] = useState<CandidateMapResponse | null>(null);
  const [mapRevisions, setMapRevisions] =
    useState<ParticipantMapStateRevision[]>([]);
  const [confirmedMapId, setConfirmedMapId] = useState("");

  const [language, setLanguage] =
    useState<SimulatorExperimentLanguage>(studyConfig.defaultLanguage);
  const [session, setSession] = useState<SimulatorExperimentSession | null>(null);
  const [resumeSessionId, setResumeSessionId] = useState(readStoredSessionId);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [humanAnswer, setHumanAnswer] = useState("");
  const [evaluation, setEvaluation] =
    useState<SimulatorSelfEvaluation>(DEFAULT_EVALUATION);

  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadBackendMaterials();
  }, []);

  const questionBank = studyMaterials?.questionBank ?? null;
  const currentQuestion = session?.questions[currentQuestionIndex] ?? null;
  const answeredCount = session?.questions.filter(
    (question) => question.simulator_answer
  ).length ?? 0;
  const evaluatedCount = session?.questions.filter(
    (question) => question.self_evaluation
  ).length ?? 0;
  const nodeById = useMemo(
    () => new Map(graphNodes.map((node) => [node.id, node])),
    [graphNodes]
  );

  async function loadBackendMaterials() {
    await runTask("loading study materials", async () => {
      const [domainCatalog, banks] = await Promise.all([
        readBenchmarkDomains(),
        listSimulatorExperimentQuestionBanks()
      ]);
      const eligibleBanks = banks.filter(
        (bank) =>
          bank.question_count >= 20
          && domainCatalog.benchmark_domains.includes(bank.benchmark_domain)
      );

      for (const bank of eligibleBanks) {
        const graphs = await listReviewedGraphs(bank.benchmark_domain);
        const selectedGraph = graphs[0];
        if (!selectedGraph) {
          continue;
        }
        const graph = await readReviewedGraph(
          bank.benchmark_domain,
          selectedGraph.version
        );
        setStudyMaterials({
          benchmarkDomain: bank.benchmark_domain,
          graphVersion: selectedGraph.version,
          questionBank: bank
        });
        setDomainSummary(
          domainCatalog.domain_summaries[bank.benchmark_domain] ?? ""
        );
        setGraphNodes(graph.authored_nodes);
        return;
      }

      throw new Error(
        eligibleBanks.length === 0
          ? "后端没有题数不少于 20 的双语题库。"
          : "后端题库已存在，但对应 domain 还没有可用的 reviewed graph。"
      );
    });
  }

  async function handleGenerateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!studyMaterials) return;
    if (!participantCode.trim()) {
      setError("请先填写匿名参与者编号。");
      return;
    }
    if (!roughDescription.trim()) {
      setError("请填写个人背景与回答偏好。");
      return;
    }
    await runTask("generating profile", async () => {
      const response = await generateProfileContextCandidate({
        benchmarkDomain: studyMaterials.benchmarkDomain,
        roughDescription: roughDescription.trim(),
        clientProvider: studyConfig.simulatorProvider
      });
      setProfileCandidate(response);
      setProfileDraft(response.candidate_profile_context);
      setConfirmedProfile(null);
      const suggestedUserId = safeSuggestedId("participant", participantCode);
      setUserId((current) => current || suggestedUserId);
      setNotice("Profile 已生成。请修订结构化字段后确认。");
    });
  }

  async function handleConfirmProfile() {
    if (!profileCandidate || !profileDraft || !userId.trim()) return;
    await runTask("confirming profile", async () => {
      const saved = await saveProfileContextCandidate(
        profileCandidate.run_id,
        profileDraft
      );
      const response = await confirmProfileContextCandidate(
        saved.run_id,
        saved.candidate_profile_context.benchmark_domain,
        userId.trim()
      );
      setProfileCandidate(saved);
      setProfileDraft(saved.candidate_profile_context);
      setConfirmedProfile(response.profile_context);
      setMapId((current) =>
        current || safeSuggestedId("simmap", participantCode)
      );
      setNotice("Profile 已确认并冻结。下一步生成个人 Knowledge Map。");
    });
  }

  async function handleGenerateMap() {
    if (!confirmedProfile || !studyMaterials) return;
    await runTask("generating map", async () => {
      const candidate = await generateCandidateMap({
        benchmarkDomain: studyMaterials.benchmarkDomain,
        graphVersion: studyMaterials.graphVersion,
        userId: confirmedProfile.user_id,
        clientProvider: studyConfig.simulatorProvider
      });
      setMapCandidate(candidate);
      setMapRevisions(
        candidate.candidate_map.states.map((state) => ({
          node_id: state.node_id,
          mastery_level: state.mastery_level,
          misconceptions: state.misconceptions,
          unknowns: state.unknowns,
          review_note: ""
        }))
      );
      setConfirmedMapId("");
      setNotice("Knowledge Map 已生成。请逐节点修订并确认。");
    });
  }

  async function handleConfirmMap() {
    if (!mapCandidate || !mapId.trim() || !studyMaterials) return;
    await runTask("confirming participant map", async () => {
      const response = await confirmParticipantMap({
        benchmarkDomain: studyMaterials.benchmarkDomain,
        candidateMapRunId: mapCandidate.run_id,
        mapId: mapId.trim(),
        revisions: mapRevisions.map((revision) => ({
          ...revision,
          review_note: revision.review_note?.trim() || null
        }))
      });
      setConfirmedMapId(response.map_manifest.map_id);
      setNotice("个人 Knowledge Map 已确认。现在可以抽取20道双语题。");
    });
  }

  async function handleCreateSession() {
    if (
      !confirmedMapId
      || !questionBank
      || !participantCode.trim()
      || !studyMaterials
    ) return;
    await runTask("creating 20-question session", async () => {
      const created = await createSimulatorExperimentSession({
        participantCode: participantCode.trim(),
        benchmarkDomain: studyMaterials.benchmarkDomain,
        mapId: confirmedMapId,
        questionBankId: questionBank.bank_id,
        language,
        simulatorClientProvider: studyConfig.simulatorProvider
      });
      setSession(created);
      storeSessionId(created.session_id);
      setResumeSessionId(created.session_id);
      setCurrentQuestionIndex(firstPendingQuestionIndex(created));
      setHumanAnswer("");
      setEvaluation(DEFAULT_EVALUATION);
      setNotice(`实验会话 ${created.session_id} 已创建，共20题。`);
    });
  }

  async function handleResumeSession() {
    if (!resumeSessionId) return;
    await runTask("resuming experiment session", async () => {
      const loaded = await readSimulatorExperimentSession(resumeSessionId);
      setSession(loaded);
      setParticipantCode(loaded.participant_code);
      setConfirmedMapId(loaded.map_id);
      setLanguage(loaded.language);
      storeSessionId(loaded.session_id);
      const index = firstPendingQuestionIndex(loaded);
      setCurrentQuestionIndex(index);
      setHumanAnswer(loaded.questions[index]?.human_answer ?? "");
      setEvaluation(
        loaded.questions[index]?.self_evaluation ?? DEFAULT_EVALUATION
      );
      setNotice(`已恢复会话 ${loaded.session_id}。`);
    });
  }

  async function handleSubmitHumanAnswer() {
    if (!session || !currentQuestion || !humanAnswer.trim()) return;
    await runTask("saving human answer and generating Simulator answer", async () => {
      const updated = await submitSimulatorExperimentHumanAnswer({
        sessionId: session.session_id,
        questionId: currentQuestion.question_id,
        humanAnswer: humanAnswer.trim()
      });
      setSession(updated);
      setNotice("真人答案和对应的 Simulator 答案已保存。请完成自评。");
    });
  }

  async function handleSaveEvaluation() {
    if (!session || !currentQuestion) return;
    await runTask("saving self-evaluation", async () => {
      const updated = await saveSimulatorExperimentSelfEvaluation({
        sessionId: session.session_id,
        questionId: currentQuestion.question_id,
        evaluation: {
          ...evaluation,
          comment: evaluation.comment?.trim() || null
        }
      });
      setSession(updated);
      const nextIndex = firstPendingQuestionIndex(updated);
      setCurrentQuestionIndex(nextIndex);
      setHumanAnswer(updated.questions[nextIndex]?.human_answer ?? "");
      setEvaluation(
        updated.questions[nextIndex]?.self_evaluation ?? DEFAULT_EVALUATION
      );
      setNotice("自评已保存。");
    });
  }

  async function handleCompleteSession() {
    if (!session) return;
    await runTask("completing experiment session", async () => {
      const completed = await completeSimulatorExperimentSession(
        session.session_id
      );
      setSession(completed);
      setNotice("实验已完成并保存。问答对已标记为待后续盲评。");
    });
  }

  function selectQuestion(index: number) {
    if (!session) return;
    const question = session.questions[index];
    setCurrentQuestionIndex(index);
    setHumanAnswer(question.human_answer ?? "");
    setEvaluation(question.self_evaluation ?? DEFAULT_EVALUATION);
  }

  function updateMapRevision(
    nodeId: string,
    patch: Partial<ParticipantMapStateRevision>
  ) {
    setMapRevisions((current) =>
      current.map((revision) =>
        revision.node_id === nodeId ? { ...revision, ...patch } : revision
      )
    );
  }

  function updateProfileList(
    field: "background" | "prior_experience" | "goals" | "preferences",
    rawValue: string
  ) {
    if (!profileDraft || confirmedProfile) return;
    setProfileDraft({
      ...profileDraft,
      [field]: lines(rawValue)
    });
  }

  async function runTask(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      await task();
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  if (!studyMaterials) {
    return (
      <main className="configuration-screen">
        <div className="configuration-card">
          <p className="eyebrow">KnowAct Simulator Test</p>
          <h1>{error ? "后端暂无可用实验材料" : "正在读取实验材料"}</h1>
          <p>
            {error
              ? error
              : "正在从 KnowAct 后端读取 domain、reviewed graph 和双语题库。"}
          </p>
          {error && (
            <button type="button" onClick={() => void loadBackendMaterials()}>
              重新读取
            </button>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="experiment-workbench">
      <section className="topbar experiment-topbar">
        <div>
          <p className="eyebrow">KnowAct / Participant Study</p>
          <h1>{studyConfig.studyTitle}</h1>
          <p>Profile → 个人 Map 校验 → 双语题库抽取20题 → 同步回答 → 个人自评 → 保存。</p>
        </div>
        <div className="deployment-badge">
          <span>{session?.benchmark_domain ?? studyMaterials.benchmarkDomain}</span>
          <strong>{studyConfig.studyId}</strong>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="experiment-scroll">
        <nav className="experiment-stepper" aria-label="Simulator experiment steps">
          <StepBadge number="1" label="Profile" complete={Boolean(confirmedProfile || session)} />
          <StepBadge number="2" label="Knowledge Map" complete={Boolean(confirmedMapId || session)} />
          <StepBadge number="3" label="20 Questions" complete={evaluatedCount === 20} />
          <StepBadge number="4" label="Saved Result" complete={session?.status === "completed"} />
        </nav>

        {!session && (
          <section className="experiment-section experiment-resume-banner">
            <div>
              <p className="eyebrow">Resume</p>
              <strong>已经开始过实验？输入恢复码继续。</strong>
            </div>
            <input
              value={resumeSessionId}
              onChange={(event) => setResumeSessionId(event.target.value)}
              placeholder="simtest_..."
              aria-label="实验恢复码"
            />
            <button
              type="button"
              className="secondary"
              onClick={() => void handleResumeSession()}
              disabled={!resumeSessionId.trim() || busy !== null}
            >
              恢复会话
            </button>
          </section>
        )}

        {!session && (
          <>
        <section className="experiment-section">
          <SectionHeading number="1" title="生成并确认个人 Profile" subtitle="只使用匿名参与者编号；生成后由本人修订。" />
          <form className="experiment-card experiment-config-grid" onSubmit={handleGenerateProfile}>
            <label>
              匿名参与者编号
              <input
                value={participantCode}
                onChange={(event) => setParticipantCode(event.target.value)}
                placeholder="例如 P001"
                disabled={busy !== null || Boolean(profileCandidate)}
                required
              />
            </label>
            <div className="experiment-meta-block">
              <span>Study configuration</span>
              <strong>
                {studyMaterials.benchmarkDomain} · {studyMaterials.graphVersion}
              </strong>
            </div>
            <div className="experiment-domain-summary">
              <strong>Domain summary</strong>
              <p>{domainSummary || "No summary configured."}</p>
            </div>
            <label className="experiment-wide">
              个人背景、学习经历、目标与回答偏好
              <textarea
                value={roughDescription}
                onChange={(event) => setRoughDescription(event.target.value)}
                placeholder="请描述你的相关学习经历、使用经验、学习目标，以及你通常如何回答不确定的问题。"
                disabled={busy !== null || Boolean(profileCandidate)}
                required
              />
            </label>
            <div className="experiment-actions experiment-wide">
              <span>系统生成结构化 Profile 后，你仍可以逐项修订。</span>
              <button type="submit" disabled={busy !== null || Boolean(profileCandidate)}>
                {profileCandidate ? "Profile 已生成" : "生成 Profile"}
              </button>
            </div>
          </form>

          {profileDraft && (
            <div className="experiment-card experiment-profile-review">
              <label className="experiment-wide">
                Summary
                <textarea
                  value={profileDraft.summary}
                  onChange={(event) => setProfileDraft({ ...profileDraft, summary: event.target.value })}
                  disabled={busy !== null || Boolean(confirmedProfile)}
                />
              </label>
              <ProfileListEditor label="Background" value={profileDraft.background} onChange={(value) => updateProfileList("background", value)} disabled={Boolean(confirmedProfile) || busy !== null} />
              <ProfileListEditor label="Prior experience" value={profileDraft.prior_experience} onChange={(value) => updateProfileList("prior_experience", value)} disabled={Boolean(confirmedProfile) || busy !== null} />
              <ProfileListEditor label="Goals" value={profileDraft.goals} onChange={(value) => updateProfileList("goals", value)} disabled={Boolean(confirmedProfile) || busy !== null} />
              <ProfileListEditor label="Preferences" value={profileDraft.preferences} onChange={(value) => updateProfileList("preferences", value)} disabled={Boolean(confirmedProfile) || busy !== null} />
              <div className="experiment-actions experiment-wide">
                <div className="experiment-meta-block">
                  <span>Participant profile ID</span>
                  <strong>{userId}</strong>
                </div>
                <button type="button" onClick={() => void handleConfirmProfile()} disabled={busy !== null || Boolean(confirmedProfile) || !userId.trim()}>
                  {confirmedProfile ? "Profile 已确认" : "保存修订并确认"}
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="experiment-section">
          <SectionHeading number="2" title="生成并校验个人 Knowledge Map" subtitle="生成结果只是草稿；参与者逐节点修订后才成为 Simulator 输入。" />
          <div className="experiment-card experiment-config-grid">
            <div className="experiment-meta-block">
              <span>Reviewed graph</span>
              <strong>{studyMaterials.graphVersion}</strong>
            </div>
            <div className="experiment-meta-block">
              <span>Confirmed profile</span>
              <strong>{confirmedProfile?.user_id ?? "等待步骤1"}</strong>
            </div>
            <div className="experiment-actions experiment-wide">
              <span>Map 生成会调用现有完整图谱 outline 与 evidence workflow。</span>
              <button type="button" onClick={() => void handleGenerateMap()} disabled={busy !== null || !confirmedProfile || Boolean(mapCandidate)}>
                {mapCandidate ? "Knowledge Map 已生成" : "生成 Knowledge Map"}
              </button>
            </div>
          </div>

          {mapCandidate && (
            <div className="experiment-map-review">
              {mapRevisions.map((revision) => {
                const node = nodeById.get(revision.node_id);
                return (
                  <article className="experiment-map-node" key={revision.node_id}>
                    <div>
                      <p className="eyebrow">{revision.node_id}</p>
                      <h3>{node?.name ?? revision.node_id}</h3>
                      <p>{node?.definition}</p>
                    </div>
                    <label>
                      Mastery
                      <select value={revision.mastery_level} onChange={(event) => updateMapRevision(revision.node_id, { mastery_level: event.target.value as MasteryLevel })} disabled={busy !== null || Boolean(confirmedMapId)}>
                        {MASTERY_LEVELS.map((level) => <option key={level}>{level}</option>)}
                      </select>
                    </label>
                    <label>
                      Misconceptions（每行一项）
                      <textarea value={revision.misconceptions.join("\n")} onChange={(event) => updateMapRevision(revision.node_id, { misconceptions: lines(event.target.value) })} disabled={busy !== null || Boolean(confirmedMapId)} />
                    </label>
                    <label>
                      Unknown boundaries（每行一项）
                      <textarea value={revision.unknowns.join("\n")} onChange={(event) => updateMapRevision(revision.node_id, { unknowns: lines(event.target.value) })} disabled={busy !== null || Boolean(confirmedMapId)} />
                    </label>
                    <label className="experiment-wide">
                      个人修订说明（可选）
                      <textarea value={revision.review_note ?? ""} onChange={(event) => updateMapRevision(revision.node_id, { review_note: event.target.value })} disabled={busy !== null || Boolean(confirmedMapId)} />
                    </label>
                  </article>
                );
              })}
              <div className="experiment-card experiment-actions">
                <div className="experiment-meta-block">
                  <span>Participant Map ID</span>
                  <strong>{mapId}</strong>
                </div>
                <button type="button" onClick={() => void handleConfirmMap()} disabled={busy !== null || Boolean(confirmedMapId) || !mapId.trim()}>
                  {confirmedMapId ? `已确认 ${confirmedMapId}` : "确认个人 Map"}
                </button>
              </div>
            </div>
          )}
        </section>
          </>
        )}

        <section className="experiment-section">
          <SectionHeading number="3" title="抽取20道题并同步回答" subtitle="每题先提交你的答案，之后才显示基于个人 Map 生成的 Simulator 答案。" />
          {!session && (
            <div className="experiment-card experiment-session-setup">
              <label>
                双语题库
                <input
                  value={
                    questionBank
                      ? `${language === "zh-CN" ? questionBank.title.zh_cn : questionBank.title.en} (${questionBank.question_count})`
                      : "正在加载部署题库…"
                  }
                  readOnly
                />
              </label>
              <label>
                题目语言
                <select value={language} onChange={(event) => setLanguage(event.target.value as SimulatorExperimentLanguage)} disabled={busy !== null}>
                  <option value="zh-CN">中文</option>
                  <option value="en">English</option>
                </select>
              </label>
              <div className="experiment-meta-block">
                <span>Sampling</span>
                <strong>20 / {questionBank?.question_count ?? 0} questions</strong>
              </div>
              <div className="experiment-actions experiment-wide">
                <span>抽样 seed 和题目顺序会随实验结果一起保存。</span>
                <button type="button" onClick={() => void handleCreateSession()} disabled={busy !== null || !confirmedMapId || !questionBank}>
                  创建20题实验
                </button>
              </div>
            </div>
          )}

          {session && currentQuestion && (
            <div className="experiment-question-layout">
              <aside className="experiment-question-index">
                <div>
                  <p className="eyebrow">Session</p>
                  <strong>{session.session_id}</strong>
                  <span>{evaluatedCount}/20 已自评</span>
                </div>
                <div className="question-index-grid">
                  {session.questions.map((question, index) => (
                    <button
                      type="button"
                      key={question.question_id}
                      className={`${index === currentQuestionIndex ? "active" : ""} ${question.self_evaluation ? "complete" : ""}`}
                      onClick={() => selectQuestion(index)}
                    >
                      {index + 1}
                    </button>
                  ))}
                </div>
              </aside>

              <div className="experiment-question-card">
                <div className="experiment-question-heading">
                  <span>Question {currentQuestionIndex + 1} / 20</span>
                  <span>{currentQuestion.question_type}</span>
                </div>
                <h2>{currentQuestion.selected_prompt}</h2>
                {!currentQuestion.simulator_answer && (
                  <>
                    <label>
                      你的回答
                      <textarea
                        className="experiment-answer-input"
                        value={humanAnswer}
                        onChange={(event) => setHumanAnswer(event.target.value)}
                        disabled={busy !== null || Boolean(currentQuestion.human_answer)}
                        placeholder="请按你当前真实理解作答，不需要查资料。"
                      />
                    </label>
                    <button type="button" onClick={() => void handleSubmitHumanAnswer()} disabled={busy !== null || !humanAnswer.trim()}>
                      提交并生成 Simulator 回答
                    </button>
                  </>
                )}

                {currentQuestion.simulator_answer && (
                  <>
                    <div className="answer-comparison-grid">
                      <AnswerPanel label="你的回答" text={currentQuestion.human_answer ?? ""} />
                      <AnswerPanel label="Simulator 回答" text={currentQuestion.simulator_answer} />
                    </div>
                    <div className="experiment-evaluation">
                      <h3>个人一致性评估</h3>
                      <p>1 表示非常不一致，5 表示非常一致。</p>
                      <RatingField label="核心内容" value={evaluation.content_similarity} onChange={(value) => setEvaluation({ ...evaluation, content_similarity: value })} disabled={session.status === "completed"} />
                      <RatingField label="知识水平" value={evaluation.knowledge_level_similarity} onChange={(value) => setEvaluation({ ...evaluation, knowledge_level_similarity: value })} disabled={session.status === "completed"} />
                      <RatingField label="能力边界" value={evaluation.boundary_similarity} onChange={(value) => setEvaluation({ ...evaluation, boundary_similarity: value })} disabled={session.status === "completed"} />
                      <RatingField label="表达方式" value={evaluation.style_similarity} onChange={(value) => setEvaluation({ ...evaluation, style_similarity: value })} disabled={session.status === "completed"} />
                      <RatingField label="整体代表性" value={evaluation.overall_representativeness} onChange={(value) => setEvaluation({ ...evaluation, overall_representativeness: value })} disabled={session.status === "completed"} />
                      <label>
                        能否替代你的回答用于后续 Agent 测试？
                        <select value={evaluation.replacement_judgement} onChange={(event) => setEvaluation({ ...evaluation, replacement_judgement: event.target.value as SimulatorSelfEvaluation["replacement_judgement"] })} disabled={session.status === "completed"}>
                          <option value="direct_use">可以直接使用</option>
                          <option value="minor_bias">基本可以，存在轻微偏差</option>
                          <option value="major_revision">需要明显修改</option>
                          <option value="not_representative">不能代表我</option>
                        </select>
                      </label>
                      <label>
                        补充说明（可选）
                        <textarea value={evaluation.comment ?? ""} onChange={(event) => setEvaluation({ ...evaluation, comment: event.target.value })} disabled={session.status === "completed"} />
                      </label>
                      <button type="button" onClick={() => void handleSaveEvaluation()} disabled={busy !== null || session.status === "completed"}>
                        保存自评并继续
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="experiment-section">
          <SectionHeading number="4" title="保存实验结果" subtitle="结果先进入受限目录；问答对盲评作为后续独立阶段。" />
          <div className="experiment-card experiment-result-summary">
            <div><span>Human + Simulator answers</span><strong>{answeredCount}/20</strong></div>
            <div><span>Self evaluations</span><strong>{evaluatedCount}/20</strong></div>
            <div><span>Blind review</span><strong>Pending</strong></div>
            <div><span>Status</span><strong>{session?.status ?? "Not started"}</strong></div>
            <button type="button" onClick={() => void handleCompleteSession()} disabled={busy !== null || !session || evaluatedCount !== 20 || session.status === "completed"}>
              {session?.status === "completed" ? "结果已保存" : "完成并保存实验"}
            </button>
            {session?.status === "completed" && (
              <p>已保存为私有实验会话：{session.session_id}。原始回答不会提交到仓库。</p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function StepBadge({ number, label, complete }: { number: string; label: string; complete: boolean }) {
  return (
    <div className={complete ? "experiment-step complete" : "experiment-step"}>
      <span>{complete ? "✓" : number}</span>
      <strong>{label}</strong>
    </div>
  );
}

function SectionHeading({ number, title, subtitle }: { number: string; title: string; subtitle: string }) {
  return (
    <header className="experiment-section-heading">
      <span>{number}</span>
      <div><h2>{title}</h2><p>{subtitle}</p></div>
    </header>
  );
}

function ProfileListEditor({ label, value, onChange, disabled }: { label: string; value: string[]; onChange: (value: string) => void; disabled: boolean }) {
  return (
    <label>
      {label}（每行一项）
      <textarea value={value.join("\n")} onChange={(event) => onChange(event.target.value)} disabled={disabled} />
    </label>
  );
}

function AnswerPanel({ label, text }: { label: string; text: string }) {
  return (
    <article className="answer-panel">
      <span>{label}</span>
      <p>{text}</p>
    </article>
  );
}

function RatingField({ label, value, onChange, disabled = false }: { label: string; value: number; onChange: (value: number) => void; disabled?: boolean }) {
  return (
    <label className="rating-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(Number(event.target.value))} disabled={disabled}>
        {[1, 2, 3, 4, 5].map((rating) => <option value={rating} key={rating}>{rating}</option>)}
      </select>
    </label>
  );
}

function firstPendingQuestionIndex(session: SimulatorExperimentSession): number {
  const index = session.questions.findIndex((question) => !question.self_evaluation);
  return index >= 0 ? index : session.questions.length - 1;
}

function lines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function safeSuggestedId(prefix: string, value: string): string {
  const slug = value.trim().replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "");
  return `${prefix}_${slug || Date.now()}`;
}

function readStoredSessionId(): string {
  try {
    return window.localStorage.getItem(sessionStorageKey()) ?? "";
  } catch {
    return "";
  }
}

function storeSessionId(sessionId: string): void {
  try {
    window.localStorage.setItem(sessionStorageKey(), sessionId);
  } catch {
    // Manual resume remains available when storage is disabled.
  }
}
