import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CandidateInterviewComponent } from './candidate-interview.component';

describe('CandidateInterviewComponent', () => {
  let component: CandidateInterviewComponent;
  let fixture: ComponentFixture<CandidateInterviewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CandidateInterviewComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CandidateInterviewComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
