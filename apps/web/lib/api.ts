/**
 * Cliente HTTP tipado de la API de Faro.
 *
 * `apps/web` solo consume contratos publicados por la API (SPEC 3): nunca abre
 * SQLite ni carga artefactos Python. Cada POST manda `Idempotency-Key`, y los
 * recursos con revisión mandan `If-Match` (SPEC 11.2).
 */

import type {
  AnswerAcceptedView,
  AnswerInteraction,
  ApiErrorBody,
  EvaluationReportView,
  FormSessionView,
  OutcomeReportResponse,
  OutcomeRequestListView,
  OutcomeValue,
  PredictionEpisodeView,
  RecommendationInboxView,
  RecommendationsView,
  ReviewDecision,
  SessionContextView,
  Source,
  SubmitFormSessionView,
} from "@/lib/contracts";

export const API_BASE =
  process.env.NEXT_PUBLIC_FARO_API ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string;

  constructor(status: number, body: ApiErrorBody | null) {
    super(body?.error.message_es ?? "Error de red");
    this.name = "ApiError";
    this.status = status;
    this.code = body?.error.code ?? "network_error";
    this.requestId = body?.error.request_id ?? "";
  }
}

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `key-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

interface RequestOptions {
  token: string;
  method?: "GET" | "POST";
  body?: unknown;
  idempotencyKey?: string;
  ifMatch?: string;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {
    Authorization: `Bearer ${options.token}`,
  };
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
    headers["Idempotency-Key"] = options.idempotencyKey ?? newIdempotencyKey();
  }
  if (options.ifMatch !== undefined) {
    headers["If-Match"] = options.ifMatch;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: method === "POST" ? JSON.stringify(options.body ?? {}) : undefined,
      signal: options.signal,
    });
  } catch {
    throw new ApiError(0, null);
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(response.status, body);
  }
  return (await response.json()) as T;
}

export const api = {
  session: (token: string, signal?: AbortSignal) =>
    request<SessionContextView>("/session", { token, signal }),

  openFormSession: (
    token: string,
    input: { subjectId: string; source: Source; sessionKind?: string },
    idempotencyKey?: string,
  ) =>
    request<FormSessionView>("/form-sessions", {
      token,
      method: "POST",
      idempotencyKey,
      body: {
        subject_id: input.subjectId,
        source: input.source,
        session_kind: input.sessionKind ?? "caregiver_daily",
      },
    }),

  readFormSession: (token: string, formSessionId: string, signal?: AbortSignal) =>
    request<FormSessionView>(`/form-sessions/${formSessionId}`, { token, signal }),

  answer: (
    token: string,
    formSessionId: string,
    input: {
      fieldCode: string;
      interaction: AnswerInteraction;
      value?: unknown;
      defaultPresentationId?: string;
    },
  ) =>
    request<AnswerAcceptedView>(`/form-sessions/${formSessionId}/answers`, {
      token,
      method: "POST",
      body: {
        field_code: input.fieldCode,
        interaction: input.interaction,
        value: input.value ?? null,
        default_presentation_id: input.defaultPresentationId ?? null,
      },
    }),

  submit: (token: string, formSessionId: string) =>
    request<SubmitFormSessionView>(`/form-sessions/${formSessionId}/submit`, {
      token,
      method: "POST",
    }),

  episode: (token: string, episodeId: string, signal?: AbortSignal) =>
    request<PredictionEpisodeView>(`/prediction-episodes/${episodeId}`, { token, signal }),

  outcomeRequests: (token: string, signal?: AbortSignal) =>
    request<OutcomeRequestListView>("/outcome-requests", { token, signal }),

  reportOutcome: (
    token: string,
    episodeId: string,
    input: { value: OutcomeValue; occurredAt?: string },
  ) =>
    request<OutcomeReportResponse>(`/prediction-episodes/${episodeId}/outcome-reports`, {
      token,
      method: "POST",
      body: { value: input.value, occurred_at: input.occurredAt ?? null },
    }),

  recommendations: (token: string, episodeId: string, signal?: AbortSignal) =>
    request<RecommendationsView>(`/prediction-episodes/${episodeId}/recommendations`, {
      token,
      signal,
    }),

  inbox: (token: string, signal?: AbortSignal) =>
    request<RecommendationInboxView>("/recommendation-instances?review_status=pending", {
      token,
      signal,
    }),

  review: (
    token: string,
    instanceId: string,
    input: {
      strategyVersionId: string;
      decision: ReviewDecision;
      humanPlan?: { actionTextEs: string; allowedExecutorRoles: string[] };
    },
    ifMatch: string,
  ) =>
    request<{ review_id: string; revision: string }>(
      `/recommendation-instances/${instanceId}/reviews`,
      {
        token,
        method: "POST",
        ifMatch,
        body: {
          strategy_version_id: input.strategyVersionId,
          decision: input.decision,
          human_plan: input.humanPlan
            ? {
                action_text_es: input.humanPlan.actionTextEs,
                allowed_executor_roles: input.humanPlan.allowedExecutorRoles,
              }
            : null,
        },
      },
    ),

  execution: (
    token: string,
    instanceId: string,
    input: {
      status: "applied" | "not_applied" | "unknown";
      strategyVersionId?: string;
      humanPlanVersionId?: string;
      appliedAt?: string;
    },
    ifMatch: string,
  ) =>
    request<{ strategy_execution_id: string; revision: string }>(
      `/recommendation-instances/${instanceId}/executions`,
      {
        token,
        method: "POST",
        ifMatch,
        body: {
          status: input.status,
          strategy_version_id: input.strategyVersionId ?? null,
          human_plan_version_id: input.humanPlanVersionId ?? null,
          applied_at: input.appliedAt ?? null,
        },
      },
    ),

  evaluation: (token: string, modelVersion: string, signal?: AbortSignal) =>
    request<EvaluationReportView>(`/evaluation/${modelVersion}`, { token, signal }),
};
