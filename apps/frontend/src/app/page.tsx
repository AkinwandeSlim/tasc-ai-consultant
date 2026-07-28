import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="text-center max-w-lg">
        <h1 className="text-heading-lg font-semibold mb-3">
          Trizen AI Solutions Consultant
        </h1>
        <p className="text-body text-muted-foreground mb-8">
          Talk to Nova and find out how Trizen can help with your business
          challenges — from AI automation to cloud infrastructure.
        </p>
        <Link
          href="/consultation"
          className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-3 text-body font-medium text-primary-foreground hover:opacity-90 transition-opacity"
        >
          Start a consultation
        </Link>
        <div className="mt-6">
          <Link
            href="/about"
            className="text-body-sm text-muted-foreground underline underline-offset-2 hover:text-foreground"
          >
            About Trizen
          </Link>
        </div>
      </div>
    </main>
  );
}
