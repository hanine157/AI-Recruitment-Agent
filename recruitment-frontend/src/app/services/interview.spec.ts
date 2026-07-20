import { TestBed } from '@angular/core/testing';

import { InterviewService } from './interview';

describe('InterviewService', () => {
  let service: InterviewService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(InterviewService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
