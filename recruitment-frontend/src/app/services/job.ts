import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class JobService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getJobs(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/jobs`);
  }
}