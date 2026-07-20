import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JobService } from '../../services/job';

@Component({
  selector: 'app-job-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './job-list.html',
  styleUrls: ['./job-list.css']
})
export class JobListComponent implements OnInit {
  jobs: any[] = [];
  loading = true;
  error = '';

  constructor(private jobService: JobService) {}

  ngOnInit() {
    this.jobService.getJobs().subscribe({
      next: (data) => {
        this.jobs = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load jobs';
        this.loading = false;
        console.error(err);
      }
    });
  }
}