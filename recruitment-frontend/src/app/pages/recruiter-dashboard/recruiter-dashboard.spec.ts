import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RecruiterDashboard } from './recruiter-dashboard';

describe('RecruiterDashboard', () => {
  let component: RecruiterDashboard;
  let fixture: ComponentFixture<RecruiterDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RecruiterDashboard],
    }).compileComponents();

    fixture = TestBed.createComponent(RecruiterDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
