"use client";

/**
 * Vista de evaluación (TAREAS P2.10).
 *
 * Muestra origen real/sintético, estimabilidad, dataset hash, modelo, métricas
 * con intervalo cuando existe, estado del challenger y limitaciones visibles.
 * Una métrica sin soporte se muestra como `not_estimable`, nunca como cero.
 */

import { useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/States";
import { ApiError, api } from "@/lib/api";
import type { EvaluationReportView } from "@/lib/contracts";
import { formatMoment } from "@/lib/format";
import { DEMO_ACCOUNTS, readToken } from "@/lib/session";

const DEFAULT_MODEL_VERSION = "synthetic-reference-mock-0.2.1";

export default function EvaluationPage() {
  const [token, setToken] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState(DEFAULT_MODEL_VERSION);
  const [report, setReport] = useState<EvaluationReportView | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setToken(readToken() ?? DEMO_ACCOUNTS[2]!.token);
  }, []);

  async function load() {
    if (token === null) return;
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      setReport(await api.evaluation(token, modelVersion));
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="faro-card space-y-2">
        <h1 className="text-lg font-semibold text-ink">Reportes de evaluación</h1>
        <label className="faro-label" htmlFor="model-version">
          Versión del modelo
        </label>
        <input
          id="model-version"
          className="faro-input"
          value={modelVersion}
          onChange={(event) => setModelVersion(event.target.value)}
        />
        <button type="button" className="faro-button-primary" onClick={() => void load()}>
          Buscar reporte
        </button>
      </section>

      {loading ? <LoadingState /> : null}
      {error !== null ? (
        <ErrorState message={error.message} requestId={error.requestId} />
      ) : null}
      {!loading && error === null && report === null ? (
        <EmptyState label="Busca una versión de modelo para ver su reporte publicado." />
      ) : null}

      {report !== null ? (
        <article className="space-y-3">
          {report.simulation_only ? (
            <p className="faro-card border-caution/40 text-sm font-semibold text-caution">
              <span aria-hidden="true">◈ </span>
              simulation_only: estas métricas no demuestran rendimiento clínico.
            </p>
          ) : null}

          <dl className="faro-card grid grid-cols-2 gap-1 text-sm">
            <dt className="text-muted">Modelo</dt>
            <dd className="text-ink">{report.model_version}</dd>
            <dt className="text-muted">Track</dt>
            <dd className="text-ink">{report.track_id}</dd>
            <dt className="text-muted">Estado del modelo</dt>
            <dd className="text-ink">{report.model_state}</dd>
            <dt className="text-muted">Origen de los datos</dt>
            <dd className="text-ink">{report.data_origin}</dd>
            <dt className="text-muted">Hash del dataset</dt>
            <dd className="break-all text-ink">{report.dataset_sha256}</dd>
            <dt className="text-muted">Definición de objetivo</dt>
            <dd className="text-ink">{report.target_definition_version ?? "—"}</dd>
            <dt className="text-muted">Protocolo</dt>
            <dd className="text-ink">{report.protocol_version}</dd>
            <dt className="text-muted">Publicado</dt>
            <dd className="text-ink">{formatMoment(report.published_at)}</dd>
          </dl>

          <table className="faro-card w-full text-sm">
            <caption className="mb-2 text-left text-base font-semibold text-ink">
              Métricas
            </caption>
            <thead>
              <tr className="text-left text-muted">
                <th scope="col">Métrica</th>
                <th scope="col">Estado</th>
                <th scope="col">Valor</th>
                <th scope="col">Intervalo</th>
              </tr>
            </thead>
            <tbody>
              {report.metrics.map((metric) => (
                <tr key={metric.name} className="border-t border-line">
                  <th scope="row" className="py-1 text-left font-normal text-ink">
                    {metric.name}
                  </th>
                  <td className="py-1 text-ink">
                    {metric.estimability === "estimable" ? "estimable" : "no estimable"}
                  </td>
                  <td className="py-1 tabular-nums text-ink">
                    {metric.value === null ? (metric.reason ?? "—") : metric.value.toFixed(3)}
                  </td>
                  <td className="py-1 tabular-nums text-ink">
                    {metric.interval === null
                      ? "—"
                      : `${metric.interval[0].toFixed(3)} – ${metric.interval[1].toFixed(3)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <section className="faro-card">
            <h2 className="text-sm font-semibold text-ink">Abstención por razón</h2>
            <dl className="mt-2 grid grid-cols-2 gap-1 text-sm">
              {Object.entries(report.abstention_by_reason).map(([reason, share]) => (
                <div key={reason} className="contents">
                  <dt className="text-muted">{reason}</dt>
                  <dd className="tabular-nums text-ink">{(share * 100).toFixed(0)}%</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="faro-card">
            <h2 className="text-sm font-semibold text-ink">Limitaciones</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
              {report.limitations_es.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </section>

          <p className="faro-card text-sm text-ink">
            El challenger real permanece en sombra durante v0.3.0: no se expone a cuidadores y
            no se despliega automáticamente.
          </p>
        </article>
      ) : null}
    </div>
  );
}
