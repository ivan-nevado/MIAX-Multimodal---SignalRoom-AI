import { PublicLayout, Section } from '@/components/layout/PublicLayout';

export default function PrivacyPage() {
  return (
    <PublicLayout
      title="Privacy notice"
      intro="SignalRoom is an educational prototype. We collect as little personal data as possible and you can delete your data at any time."
    >
      <Section title="What we store">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            Your email address and account identifier (managed by Amazon Cognito; we never see your password
            in the cloud deployment).
          </li>
          <li>Your preferences (timezone, daily briefing settings) and your watchlist.</li>
          <li>
            Your investigations, follow-up questions, briefings and the files you upload (PDFs, images,
            audio).
          </li>
        </ul>
        <p>We do not store banking data, portfolio holdings or payment information.</p>
      </Section>
      <Section title="How your files are protected">
        <p>
          Uploaded files and generated media are stored in a private, encrypted storage bucket under a folder
          that belongs to your account. They are only accessible through short-lived signed links and are
          deleted automatically after 90 days. Logs never contain document contents, transcripts, passwords or
          access tokens.
        </p>
      </Section>
      <Section title="Third-party processing">
        <p>
          To analyse your question and files, relevant content is sent to AI model providers (via OpenRouter:
          OpenAI and Google models) and public market-data sources (Yahoo Finance, SEC EDGAR, GDELT, and
          optionally Alpha Vantage and FRED). These providers process the content to return results;
          SignalRoom does not sell or share your data for advertising.
        </p>
      </Section>
      <Section title="Emails">
        <p>
          We only email you the daily briefing if you enable it in Settings. Every email contains a link to
          manage your preferences or unsubscribe.
        </p>
      </Section>
      <Section title="Your rights">
        <p>
          You can delete your investigations, briefings, uploaded files and watchlist at any time from
          Settings → Data &amp; privacy. For any other request (access, rectification, account removal)
          contact the SignalRoom team.
        </p>
      </Section>
    </PublicLayout>
  );
}
