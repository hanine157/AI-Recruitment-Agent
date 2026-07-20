import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { InterviewService } from '../../services/interview';

@Component({
  selector: 'app-schedule',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './schedule.html',
  styleUrl: './schedule.css'
})
export class ScheduleComponent implements OnInit {
  token: string = '';
  interview: any = null;
  loading = true;
  error = '';
  submitting = false;
  confirmed = false;

  selectedSlot: string | null = null;
  customDate: string = '';
  customTime: string = '';

  constructor(
    private route: ActivatedRoute,
    private interviewService: InterviewService,
    private cdr: ChangeDetectorRef   // 🆕
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.interviewService.getInterviewByToken(this.token).subscribe({
      next: (data) => {
        this.interview = data;
        this.loading = false;
        this.cdr.detectChanges();   // 🆕
      },
      error: (err) => {
        this.error = err.status === 404
          ? 'This interview link is invalid or has expired.'
          : 'Failed to load interview details.';
        this.loading = false;
        this.cdr.detectChanges();   // 🆕
      }
    });
  }

  selectSlot(slot: string) {
    this.selectedSlot = slot;
    this.customDate = '';
    this.customTime = '';
  }

  onCustomDateChange() {
    this.selectedSlot = null;
  }

  get canSubmit(): boolean {
    if (this.selectedSlot) return true;
    return !!(this.customDate && this.customTime);
  }

  confirmSchedule() {
    if (!this.canSubmit) return;

    let scheduledAt: string;
    let mode: 'slot' | 'free';

    if (this.selectedSlot) {
      scheduledAt = this.selectedSlot;
      mode = 'slot';
    } else {
      scheduledAt = `${this.customDate}T${this.customTime}:00`;
      mode = 'free';
    }

    this.submitting = true;
    this.interviewService.scheduleInterview(this.token, scheduledAt, mode).subscribe({
      next: (response) => {
        console.log('Schedule success response:', response);
        this.submitting = false;
        this.confirmed = true;
        this.cdr.detectChanges();   // 🆕 force UI update regardless of zone issues
      },
      error: (err) => {
        this.submitting = false;
        this.error = err.error?.detail || 'Failed to schedule the interview. Please try again.';
        this.cdr.detectChanges();   // 🆕
      }
    });
  }

  get hasSlots(): boolean {
    return !!(this.interview?.available_slots && this.interview.available_slots.length > 0);
  }

  get minDate(): string {
    return new Date().toISOString().split('T')[0];
  }
}