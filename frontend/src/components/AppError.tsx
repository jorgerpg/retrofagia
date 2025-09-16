import { isRouteErrorResponse, useRouteError } from "react-router-dom";

export default function AppError() {
  const error = useRouteError();
  const msg = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : (error as any)?.message || "Algo deu errado";
  return (
    <div className="min-h-screen bg-app grid place-items-center">
      <div className="card p-6 w-[90%] max-w-md text-center">
        <h1 className="text-2xl font-bold">Ops…</h1>
        <p className="text-white/70 mt-2">{msg}</p>
      </div>
    </div>
  );
}
