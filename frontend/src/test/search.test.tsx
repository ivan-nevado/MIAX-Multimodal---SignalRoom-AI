import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MultimodalPanel } from '@/components/investigations/MultimodalPanel';
import { api } from '@/lib/api';
import SearchPage from '@/pages/SearchPage';
import type { SearchResponse } from '@/types/api';
import { makeResult, renderWithProviders } from './utils';

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, api: { search: vi.fn(), searchByImage: vi.fn(), transcript: vi.fn() } };
});

const response: SearchResponse = {
  query: 'gross margin',
  mode: 'semantic',
  indexed_investigations: 2,
  hits: [
    {
      investigation_id: 'inv_7',
      symbol: null,
      asset_name: null,
      question: 'Summarize this webinar',
      created_at: new Date().toISOString(),
      modality: 'video',
      title: 'webinar.mp4 - transcript',
      snippet: 'CFO: Gross margin was 61.5%, down 120 basis points on logistics.',
      ref: 'up_1',
      location: '00:56',
      score: 0.79,
    },
  ],
};

beforeEach(() => vi.clearAllMocks());

describe('semantic search page', () => {
  it('searches by meaning, filters by modality and links to the investigation', async () => {
    vi.mocked(api.search).mockResolvedValue(response);
    renderWithProviders(<SearchPage />);
    await userEvent.type(screen.getByLabelText('Search your research'), 'gross margin');
    expect(await screen.findByText('webinar.mp4 - transcript')).toBeInTheDocument();
    expect(screen.getByText('00:56')).toBeInTheDocument();
    expect(screen.getByText(/Semantic match/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /webinar\.mp4/ })).toHaveAttribute(
      'href',
      '/app/investigation/inv_7',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Video' }));
    await waitFor(() => expect(api.search).toHaveBeenLastCalledWith('gross margin', 'video'));
  });

  it('searches by image and shows an empty state', async () => {
    vi.mocked(api.searchByImage).mockResolvedValue({ ...response, mode: 'image', hits: [] });
    renderWithProviders(<SearchPage />);
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'chart.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Query image'), file);
    expect(await screen.findByText('No matching passages')).toBeInTheDocument();
    expect(api.searchByImage).toHaveBeenCalledWith(file, 'all');
  });

  it('offers suggestions before typing', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByRole('button', { name: 'export restrictions' })).toBeInTheDocument();
    expect(api.search).not.toHaveBeenCalled();
  });
});

describe('video findings', () => {
  it('renders slides with timestamps and figures', () => {
    const result = {
      ...makeResult(),
      videos: [
        {
          upload_id: 'up_v',
          filename: 'webinar.mp4',
          summary: 'Results webinar.',
          language: 'en',
          speakers: ['CEO'],
          segment_count: 6,
          transcript_preview: [],
          slides: [
            {
              timestamp: '01:20',
              title: 'Q4 FY2026 Outlook',
              description: 'Guidance slide',
              figures: [{ fact: 'Revenue guidance', value: '$4.0B - $4.2B', page: null }],
            },
          ],
          key_points: ['Record revenue'],
          guidance: ['Q4 revenue $4.0-4.2B'],
          management_tone: 'cautious',
          risks: ['Export licences'],
          notable_quotes: [],
          source_id: 'src_video_up_v',
        },
      ],
    };
    renderWithProviders(<MultimodalPanel result={result} investigationId="inv_1" />);
    expect(screen.getByText('Q4 FY2026 Outlook')).toBeInTheDocument();
    expect(screen.getByText('$4.0B - $4.2B')).toBeInTheDocument();
    expect(screen.getByText('01:20')).toBeInTheDocument();
  });
});
