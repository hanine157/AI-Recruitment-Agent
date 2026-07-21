import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CandidateInterviewComponent } from './candidate-interview.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';

describe('CandidateInterviewComponent', () => {
  let component: CandidateInterviewComponent;
  let fixture: ComponentFixture<CandidateInterviewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CandidateInterviewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => 'mock-token',
              },
            },
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CandidateInterviewComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
