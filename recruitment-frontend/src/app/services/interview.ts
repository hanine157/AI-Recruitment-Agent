import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class InterviewService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getInterviewByToken(token: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/interviews/token/${token}`);
  }

  scheduleInterview(token: string, scheduledAt: string, mode: 'slot' | 'free'): Observable<any> {
    return this.http.patch<any>(`${this.baseUrl}/interviews/${token}/schedule`, {
      scheduled_at: scheduledAt,
      mode: mode
    });
  }
}