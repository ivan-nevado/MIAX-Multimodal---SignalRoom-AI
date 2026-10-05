import {
  DailyBriefingSection,
  EvidenceSection,
  Hero,
  Multimodal,
  Pricing,
  Problem,
  Team,
  WhyCard,
} from '@/features/landing/LandingSections';
import { PublicFooter, PublicHeader } from '@/components/layout/PublicLayout';
import { SectionTitle } from '@/components/ui/misc';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicHeader />
      <main>
        <Hero />
        <Problem />
        <Team />
        <Multimodal />
        <section className="px-4 py-20 sm:px-6">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
            <SectionTitle
              eyebrow="Why?"
              title="The question every investor asks. Answered with evidence."
              description="Click “Why?” on any asset. The team measures the move, finds and clusters the news, checks filings and macro, scores likely drivers transparently and writes a brief you can understand in 30 seconds."
            />
            <WhyCard />
          </div>
        </section>
        <DailyBriefingSection />
        <EvidenceSection />
        <Pricing />
      </main>
      <PublicFooter />
    </div>
  );
}
