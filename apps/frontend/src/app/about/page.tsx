import Link from "next/link";

export default function AboutPage() {
  return (
    <main className="min-h-screen px-4 py-12">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="text-body-sm text-muted-foreground underline underline-offset-2 hover:text-foreground mb-6 inline-block"
        >
          &larr; Back
        </Link>
        <h1 className="text-heading-lg font-semibold mb-4">About Trizen Ventures</h1>
        <div className="text-body text-muted-foreground space-y-4">
          <p>
            Trizen Ventures is a technology consultancy specialising in AI automation,
            software development, data engineering, and cloud infrastructure.
          </p>
          <p>
            Our AI Solutions Consultant, Nova, helps visitors understand how Trizen
            can address their business challenges through a structured discovery
            conversation.
          </p>
          <p>
            Nova uses a curated knowledge base to provide grounded answers about
            Trizen services, case studies, and capabilities.
          </p>
        </div>
      </div>
    </main>
  );
}
