import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

type Candidate = {
  id: number;
  first_name: string;
  last_name: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  status: string;
  cv_text?: string | null;
};

type Job = {
  id: number;
  title: string;
  department?: string | null;
  description?: string | null;
  required_skills?: string | null;
  created_at?: string;
};

type Interview = {
  token?: string | null;
  status: string;
  scheduled_at?: string | null;
  available_slots?: string[] | null;
  candidate?: {
    id?: number;
    first_name?: string;
    last_name?: string;
    firstName?: string;
    lastName?: string;
    email?: string;
  } | null;
  job?: {
    id?: number;
    title?: string;
  } | null;
};

type CalendarDay = {
  date: Date;
  inMonth: boolean;
  isToday: boolean;
  interviews: Interview[];
};

@Component({
  selector: 'app-recruiter-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './recruiter-dashboard.html',
  styleUrl: './recruiter-dashboard.css',
})
export class RecruiterDashboardComponent implements OnInit, OnDestroy {
  candidates: Candidate[] = [];
  jobs: Job[] = [];
  interviews: Interview[] = [];

  showSlotsModal = false;
  selectedInterview: Interview | null = null;
  slotInputs: string[] = ['', '', '', ''];

  showAssignJobModal = false;
  selectedCandidate: Candidate | null = null;
  selectedJobId: number | null = null;

  uploadingCv = false;
  cvUploadSuccess = false;
  selectedCandidateForCv: Candidate | null = null;
  showCvUploadModal = false;

  loading = true;
  error = '';
  refreshInterval: ReturnType<typeof setInterval> | null = null;

  today = new Date();
  viewedMonth = new Date();
  recruiterName = 'Hanine';
  avatarPalette = ['#2F5FFF', '#9333EA', '#059669', '#D97706', '#DB2777', '#0891B2'];

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadData();
    this.refreshInterval = setInterval(() => this.loadData(), 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  loadData(): void {
    this.http.get<Candidate[]>('http://localhost:8000/candidates').subscribe({
      next: (data) => {
        this.candidates = (data ?? []).map((candidate) => this.normalizeCandidate(candidate));
        this.loading = false;
        this.error = '';
      },
      error: () => {
        this.error = 'Failed to load candidates';
        this.loading = false;
      },
    });

    this.http.get<Job[]>('http://localhost:8000/jobs').subscribe({
      next: (data) => {
        this.jobs = data ?? [];
      },
      error: (err) => console.error('Failed to load jobs', err),
    });

    this.http.get<Interview[]>('http://localhost:8000/interviews').subscribe({
      next: (data) => {
        this.interviews = (data ?? []).map((interview) => this.normalizeInterview(interview));
      },
      error: (err) => console.error('Failed to load interviews', err),
    });
  }

  private normalizeCandidate(candidate: Candidate): Candidate {
    return {
      ...candidate,
      firstName: candidate.firstName ?? candidate.first_name,
      lastName: candidate.lastName ?? candidate.last_name,
    };
  }

  private normalizeInterview(interview: Interview): Interview {
    return {
      ...interview,
      candidate: interview.candidate
        ? {
            ...interview.candidate,
            firstName: interview.candidate.firstName ?? interview.candidate.first_name,
            lastName: interview.candidate.lastName ?? interview.candidate.last_name,
          }
        : interview.candidate,
    };
  }

  changeStatus(candidate: Candidate, newStatus: string): void {
    if (!newStatus) return;

    if (newStatus === 'To Interview') {
      this.selectedCandidate = candidate;
      this.selectedJobId = null;
      this.showAssignJobModal = true;
      return;
    }

    this.http
      .patch(`http://localhost:8000/candidates/${candidate.id}/status`, { status: newStatus })
      .subscribe({
        next: () => this.loadData(),
        error: (err) => console.error('Failed to update status', err),
      });
  }

  closeModal(): void {
    this.showAssignJobModal = false;
    this.selectedCandidate = null;
    this.selectedJobId = null;
  }

  confirmAssignJob(): void {
    if (!this.selectedJobId || !this.selectedCandidate) return;

    this.http
      .patch(`http://localhost:8000/candidates/${this.selectedCandidate.id}/status`, {
        status: 'To Interview',
        job_id: this.selectedJobId,
      })
      .subscribe({
        next: () => {
          this.closeModal();
          this.loadData();
        },
        error: (err) => console.error('Failed to assign job', err),
      });
  }

  private getScheduledAt(interview: Interview | null | undefined): string | null {
    return interview?.scheduled_at ?? null;
  }

  getInterviewForCandidate(candidateId: number): Interview | undefined {
    return this.interviews.find((interview) => interview.candidate?.id === candidateId);
  }

  getJobTitleForCandidate(candidateId: number): string {
    const interview = this.getInterviewForCandidate(candidateId);
    if (!interview) return '—';
    return interview.job?.title ?? 'Unknown Job';
  }

  getScheduledAtForCandidate(candidateId: number): string | null {
    const interview = this.getInterviewForCandidate(candidateId);
    return interview ? this.getScheduledAt(interview) : null;
  }

  getCandidateName(candidateOrInterview: number | Interview): string {
    if (typeof candidateOrInterview === 'number') {
      const candidate = this.candidates.find((c) => c.id === candidateOrInterview);
      return candidate ? `${candidate.first_name} ${candidate.last_name}`.trim() : 'Unknown';
    }

    return candidateOrInterview?.candidate
      ? `${candidateOrInterview.candidate.first_name ?? ''} ${candidateOrInterview.candidate.last_name ?? ''}`.trim()
      : 'Unknown';
  }

  getJobTitle(interview: Interview): string {
    return interview?.job?.title ?? 'Unknown Job';
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'Applied':
        return 'status-applied';
      case 'To Interview':
        return 'status-to-interview';
      case 'Waiting Confirmation':
        return 'status-waiting';
      case 'Interview Scheduled':
        return 'status-scheduled';
      case 'In Progress':
        return 'status-in-progress';
      case 'Interview Completed':
        return 'status-completed';
      case 'Hired':
        return 'status-hired';
      case 'Rejected':
        return 'status-rejected';
      default:
        return 'status-default';
    }
  }

  initials(first?: string, last?: string): string {
    return ((first?.[0] || '') + (last?.[0] || '')).toUpperCase();
  }

  avatarColor(name?: string): string {
    if (!name) return this.avatarPalette[0];

    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }

    return this.avatarPalette[Math.abs(hash) % this.avatarPalette.length];
  }

  isSameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }

  prevMonth(): void {
    this.viewedMonth = new Date(this.viewedMonth.getFullYear(), this.viewedMonth.getMonth() - 1, 1);
  }

  nextMonth(): void {
    this.viewedMonth = new Date(this.viewedMonth.getFullYear(), this.viewedMonth.getMonth() + 1, 1);
  }

  goToToday(): void {
    this.viewedMonth = new Date();
  }

  get calendarWeeks(): CalendarDay[][] {
    const year = this.viewedMonth.getFullYear();
    const month = this.viewedMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const start = new Date(firstDay);
    start.setDate(firstDay.getDate() - startOffset);

    const weeks: CalendarDay[][] = [];
    let current = new Date(start);

    for (let w = 0; w < 6; w++) {
      const week: CalendarDay[] = [];

      for (let d = 0; d < 7; d++) {
        const dayDate = new Date(current);
        const dayInterviews = this.interviews.filter((interview) => {
          const scheduledAt = this.getScheduledAt(interview);
          return scheduledAt !== null && this.isSameDay(new Date(scheduledAt), dayDate);
        });

        week.push({
          date: dayDate,
          inMonth: dayDate.getMonth() === month,
          isToday: this.isSameDay(dayDate, new Date()),
          interviews: dayInterviews,
        });

        current.setDate(current.getDate() + 1);
      }

      weeks.push(week);
    }

    return weeks;
  }

  get upcomingInterviews(): Interview[] {
    return this.interviews
      .filter((interview) => this.getScheduledAt(interview))
      .sort((a, b) => {
        const aTime = this.getScheduledAt(a);
        const bTime = this.getScheduledAt(b);
        return (aTime ? new Date(aTime).getTime() : 0) - (bTime ? new Date(bTime).getTime() : 0);
      })
      .slice(0, 6);
  }

  get totalCandidates(): number {
    return this.candidates.length;
  }

  get totalJobs(): number {
    return this.jobs.length;
  }

  get inProgressInterviews(): number {
    return this.interviews.filter((interview) => interview.status === 'In Progress').length;
  }

  get completedInterviews(): number {
    return this.candidates.filter((candidate) => candidate.status === 'Interview Completed').length;
  }

  openInterview(candidate: Candidate): void {
    const interview = this.getInterviewForCandidate(candidate.id);

    if (!interview?.token) {
      alert('Interview not found.');
      return;
    }

    this.router.navigate(['/interview', interview.token]);
  }

  openSlotsModal(interview: Interview | undefined): void {
    if (!interview) return;

    this.selectedInterview = interview;
    this.showSlotsModal = true;
  }

  saveSlots(): void {
    if (!this.selectedInterview?.token) {
      console.error('Cannot save slots without a selected interview token.');
      return;
    }

    const slots = this.slotInputs.filter((slot) => slot !== '');

    this.http
      .patch(`http://localhost:8000/interviews/${this.selectedInterview.token}/availability`, {
        slots,
      })
      .subscribe({
        next: () => {
          alert('Slots saved successfully!');
          this.closeSlotsModal();
          this.loadData();
        },
        error: (err) => {
          console.error(err);
          alert('Failed to save slots.');
        },
      });
  }

  closeSlotsModal(): void {
    this.showSlotsModal = false;
    this.selectedInterview = null;
    this.slotInputs = ['', '', '', ''];
  }

  getRecruiterAction(candidate: Candidate): string {
    const interview = this.getInterviewForCandidate(candidate.id);

    if (candidate.status === 'Applied') {
      return 'change-status';
    }

    if (!interview) {
      return 'none';
    }

    switch (interview.status) {
      case 'Waiting Candidate Choice':
        return 'waiting';
      case 'Scheduled':
        return 'view-interview';
      case 'In Progress':
        return 'live';
      case 'Completed':
        return 'view-report';
      default:
        return 'set-slots';
    }
  }

  openCvUpload(candidate: Candidate): void {
    this.selectedCandidateForCv = candidate;
    this.showCvUploadModal = true;
  }

  closeCvUpload(): void {
    this.showCvUploadModal = false;
    this.selectedCandidateForCv = null;
    this.uploadingCv = false;
    this.cvUploadSuccess = false;
  }

  uploadCv(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please upload a PDF file only');
      return;
    }

    if (!this.selectedCandidateForCv) {
      alert('Please select a candidate first.');
      return;
    }

    this.uploadingCv = true;
    this.cvUploadSuccess = false;

    const formData = new FormData();
    formData.append('file', file);

    this.http
      .post(`http://localhost:8000/candidates/${this.selectedCandidateForCv.id}/cv`, formData)
      .subscribe({
        next: () => {
          this.uploadingCv = false;
          this.cvUploadSuccess = true;
          this.loadData();
        },
        error: (err) => {
          console.error('CV upload failed:', err);
          this.uploadingCv = false;
          alert('Failed to upload CV. Please try again.');
        },
      });
  }
}
