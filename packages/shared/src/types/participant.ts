export interface Participant {
  id: string;
  meetingId: string;
  name: string;
  email?: string;
  speakerLabel?: string;
  joinedAt?: string;
  leftAt?: string;
}
