import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Inject,
  NgZone,
  OnDestroy,
  OnInit,
  PLATFORM_ID,
  ViewChild,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

type InterviewMessage = {
  role: 'ai' | 'candidate';
  content: string;
};

@Component({
  selector: 'app-candidate-interview',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './candidate-interview.component.html',
  styleUrl: './candidate-interview.component.css',
})
export class CandidateInterviewComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('chatBox') chatBox!: ElementRef<HTMLElement>;
  private faceapi: any;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly http: HttpClient,
    private readonly ngZone: NgZone,
    private readonly cdr: ChangeDetectorRef,
    @Inject(PLATFORM_ID) private readonly platformId: object,
  ) { }

  token = '';
  messages: InterviewMessage[] = [];
  userInput = '';
  loading = false;
  interviewStarted = false;
  interviewCompleted = false;
  candidateName = '';
  jobTitle = '';
  questionsAsked = 0;

  modelsLoaded = false;
  faceDetected = false;
  currentExpression = '-';
  eyeContactEstimate = 0;
  attentionLevel = '-';
  // 🆕 Voice input state
  isRecording = false;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

  private detectionInterval: ReturnType<typeof setInterval> | null = null;
  private metricsSaveInterval: ReturnType<typeof setInterval> | null = null;
  private isDetecting = false;

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
  }

  async ngAfterViewInit() {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      const video = this.videoElement?.nativeElement;

      if (!video) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      video.srcObject = stream;
      await video.play();
      const module = await import('@vladmandic/face-api');
      this.faceapi = module;

      await this.loadFaceModels();
    } catch (err) {
      console.error('Failed to start camera:', err);
    }
  }

  ngOnDestroy() {
    if (this.detectionInterval) {
      clearInterval(this.detectionInterval);
      this.detectionInterval = null;
    }
    if (this.metricsSaveInterval) {
      clearInterval(this.metricsSaveInterval);
    }

    const video = this.videoElement?.nativeElement;
    const stream = video?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((track) => track.stop());
  }

  async loadFaceModels() {
    try {
      const modelUrl = '/models';

      await Promise.all([
        this.faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl),
        this.faceapi.nets.faceLandmark68Net.loadFromUri(modelUrl),
        this.faceapi.nets.faceExpressionNet.loadFromUri(modelUrl),
      ]);

      this.modelsLoaded = true;
      this.ngZone.runOutsideAngular(() => {
        this.startFaceDetection();
      });
    } catch (err) {
      console.error('Failed to load face-api models:', err);
    }
  }

  startFaceDetection() {
    const video = this.videoElement?.nativeElement;
    if (!video) return;

    if (this.detectionInterval) {
      clearInterval(this.detectionInterval);
    }

    this.detectionInterval = setInterval(async () => {
      if (!this.modelsLoaded || video.paused || video.ended) return;
      if (this.isDetecting) return;
      if (video.videoWidth === 0 || video.videoHeight === 0) return;

      this.isDetecting = true;
      try {
        const result = await this.faceapi
          .detectSingleFace(video, new this.faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks()
          .withFaceExpressions();

        this.ngZone.run(() => {
          if (result) {
            const expressions = result.expressions;
            const topExpression = (Object.entries(expressions) as [string, number][]).sort((a, b) => b[1] - a[1])[0];

            this.faceDetected = true;
            this.currentExpression = topExpression ? topExpression[0] : '-';
            this.eyeContactEstimate = Math.max(0, Math.min(100, Math.round((result.detection.score ?? 0) * 100)));
            this.attentionLevel = this.eyeContactEstimate >= 75 ? 'High' : this.eyeContactEstimate >= 50 ? 'Medium' : 'Low';
          } else {
            this.faceDetected = false;
            this.currentExpression = '-';
            this.eyeContactEstimate = 0;
            this.attentionLevel = 'No face detected';
          }

          this.cdr.detectChanges();
        });
      } catch (err) {
        console.error('Detection error:', err);
      } finally {
        this.isDetecting = false;
      }
    }, 3000);
  }

  startInterview() {
    this.ngZone.run(() => {
      this.loading = true;
      this.http.post<any>(`http://localhost:8000/interviews/${this.token}/start`, {}).subscribe({
        next: (data) => {
          this.ngZone.run(() => {
            this.interviewStarted = true;
            this.candidateName = data.candidate;
            this.jobTitle = data.job;
            this.messages = [
              {
                role: 'ai',
                content: data.first_question,
              },
            ];
            this.questionsAsked = 1;
            this.loading = false;
            this.cdr.detectChanges();
            this.scrollToBottom();
            this.startMetricsSaving();
          });
        },
        error: (err) => {
          console.error('Error:', err);
          this.ngZone.run(() => {
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
      });
    });
  }

  sendMessage() {
    if (!this.userInput.trim() || this.loading) return;

    const answer = this.userInput.trim();

    this.ngZone.run(() => {
      this.userInput = '';
      this.messages.push({
        role: 'candidate',
        content: answer,
      });
      this.loading = true;
      this.cdr.detectChanges();
      this.scrollToBottom();

      this.http.post<any>(`http://localhost:8000/interviews/${this.token}/message`, { content: answer }).subscribe({
        next: (data) => {
          this.ngZone.run(() => {
            this.messages.push({
              role: 'ai',
              content: data.response,
            });
            this.questionsAsked += 1;
            if (data.interview_ended) {
              this.interviewCompleted = true;
            }
            this.loading = false;
            this.cdr.detectChanges();
            this.scrollToBottom();
          });
        },
        error: (err) => {
          console.error('Error:', err);
          this.ngZone.run(() => {
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
      });
    });
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      const chatBox = this.chatBox?.nativeElement;
      if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
      }
    }, 100);
  }

  private startMetricsSaving(): void {
    if (!isPlatformBrowser(this.platformId) || this.metricsSaveInterval) return;

    this.metricsSaveInterval = setInterval(() => {
      if (!this.faceDetected || !this.interviewStarted || this.interviewCompleted) return;

      this.http.post(`http://localhost:8000/interviews/${this.token}/face-metrics`, {
        eye_contact: this.eyeContactEstimate,
        expression: this.currentExpression,
        attention_level: this.attentionLevel,
      }).subscribe({
        error: (err) => console.error('Failed to save face metric:', err),
      });
    }, 30000);
  }

  // 🆕 Voice input methods
  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(stream);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        console.log('Audio recorded:', audioBlob.size, 'bytes'); // temporary check for today
        stream.getTracks().forEach(track => track.stop()); // release the mic
      };

      this.mediaRecorder.start();
      this.ngZone.run(() => {
        this.isRecording = true;
        this.cdr.detectChanges();
      });
    } catch (err) {
      console.error('Microphone access error:', err);
      alert('Could not access microphone. Please check permissions.');
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.ngZone.run(() => {
        this.isRecording = false;
        this.cdr.detectChanges();
      });
    }
  }
}