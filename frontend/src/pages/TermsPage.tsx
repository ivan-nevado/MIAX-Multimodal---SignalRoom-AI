import { PublicLayout, Section } from '@/components/layout/PublicLayout';

export default function TermsPage() {
  return (
    <PublicLayout
      title="Terms of use"
      intro="By using SignalRoom you accept these terms. SignalRoom is an educational research prototype operated for an academic programme."
    >
      <Section title="No investment advice">
        <p>
          SignalRoom is an educational financial research prototype. Its analysis is generated from available
          data and AI models and may contain errors. It does not provide personalized investment advice,
          execute trades, or guarantee the accuracy or completeness of market information. Nothing in
          SignalRoom is a recommendation to buy, sell or hold any asset.
        </p>
      </Section>
      <Section title="Data accuracy">
        <p>
          Market data may be delayed and comes from free public sources. Likely drivers and their
          “evidence-weighted contribution” are heuristics based on available sources — they are not
          probabilities and do not prove causality.
        </p>
      </Section>
      <Section title="Access">
        <p>
          The demo deployment may be invite-only and subject to daily usage limits to control costs. Access
          can be revoked at any time. Do not attempt to bypass access controls, rate limits or security
          measures.
        </p>
      </Section>
      <Section title="Your content">
        <p>
          Only upload documents, images and audio you are allowed to share. Do not upload confidential,
          personal or copyrighted material you do not have rights to. You keep ownership of your content; you
          can delete it from Settings.
        </p>
      </Section>
      <Section title="Availability">
        <p>
          The service is provided “as is”, without warranties, and may be interrupted or discontinued at any
          time when the academic project ends.
        </p>
      </Section>
    </PublicLayout>
  );
}
