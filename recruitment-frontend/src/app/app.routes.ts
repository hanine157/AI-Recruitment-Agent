import { Routes } from '@angular/router';
import { RecruiterDashboardComponent } from './pages/recruiter-dashboard/recruiter-dashboard';
import { JobListComponent } from './pages/job-list/job-list';
import { ScheduleComponent } from './pages/schedule/schedule';

export const routes: Routes = [
  {
    path: 'interview/:token',
    loadComponent: () =>
      import('./pages/candidate-interview/candidate-interview.component').then((m) => m.CandidateInterviewComponent),
  },
  { path: 'dashboard', component: RecruiterDashboardComponent },
  { path: 'jobs', component: JobListComponent },
  { path: 'schedule/:token', component: ScheduleComponent },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' }
];
