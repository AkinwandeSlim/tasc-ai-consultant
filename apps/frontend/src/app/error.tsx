"use client";

export default function ErrorPage({
  error: _error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h2 className="text-heading-md font-semibold mb-2">
          Something went wrong
        </h2>
        <p className="text-body text-muted-foreground mb-6">
          The consultation service encountered an error. Please try again.
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-body-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
