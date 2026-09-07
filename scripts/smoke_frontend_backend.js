async function main() {
  const backendUrl = process.env.BACKEND_URL?.replace(/\/+$/, "");

  if (!backendUrl) {
    throw new Error("BACKEND_URL is required for the frontend-to-backend smoke check");
  }

  const response = await fetch(`${backendUrl}/health`, {
    signal: AbortSignal.timeout(10_000),
  });

  if (!response.ok) {
    throw new Error(`backend health check failed with HTTP ${response.status}`);
  }

  const result = await response.json();
  if (result.status !== "ok") {
    throw new Error(`unexpected backend health response: ${JSON.stringify(result)}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
