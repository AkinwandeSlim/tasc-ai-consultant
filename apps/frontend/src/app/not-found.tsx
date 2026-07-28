import Link from "next/link";

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h2 className="text-heading-md font-semibold mb-2">Page not found</h2>
        <p className="text-body text-muted-foreground mb-6">
          The page you are looking for does not exist.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-body-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
        >
          Go home
        </Link>
      </div>
    </main>
  );
}
