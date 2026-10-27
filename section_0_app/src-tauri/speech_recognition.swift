import AVFoundation
import Foundation
import Speech

func emit(_ payload: [String: Any]) {
    guard
        let data = try? JSONSerialization.data(withJSONObject: payload),
        let line = String(data: data, encoding: .utf8)
    else {
        return
    }
    print(line)
    fflush(stdout)
}

func requestSpeechAuthorization() -> SFSpeechRecognizerAuthorizationStatus {
    let semaphore = DispatchSemaphore(value: 0)
    var status = SFSpeechRecognizer.authorizationStatus()
    if status == .notDetermined {
        SFSpeechRecognizer.requestAuthorization { result in
            status = result
            semaphore.signal()
        }
        semaphore.wait()
    }
    return status
}

func requestMicrophoneAuthorization() -> Bool {
    switch AVCaptureDevice.authorizationStatus(for: .audio) {
    case .authorized:
        return true
    case .notDetermined:
        let semaphore = DispatchSemaphore(value: 0)
        var granted = false
        AVCaptureDevice.requestAccess(for: .audio) { result in
            granted = result
            semaphore.signal()
        }
        semaphore.wait()
        return granted
    default:
        return false
    }
}

let localeIdentifier = CommandLine.arguments.dropFirst().first ?? Locale.current.identifier
guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: localeIdentifier)) else {
    emit(["kind": "error", "message": "Speech recognition is unavailable for \(localeIdentifier)."])
    exit(1)
}

let speechStatus = requestSpeechAuthorization()
guard speechStatus == .authorized else {
    emit(["kind": "error", "message": "Allow Speech Recognition for AI Friend in System Settings > Privacy & Security > Speech Recognition."])
    exit(1)
}

guard requestMicrophoneAuthorization() else {
    emit(["kind": "error", "message": "Allow microphone access for AI Friend in System Settings > Privacy & Security > Microphone."])
    exit(1)
}

let engine = AVAudioEngine()
let request = SFSpeechAudioBufferRecognitionRequest()
request.shouldReportPartialResults = true

let input = engine.inputNode
let format = input.outputFormat(forBus: 0)
guard format.channelCount > 0 else {
    emit(["kind": "error", "message": "No microphone input is available."])
    exit(1)
}

input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
    request.append(buffer)
}

do {
    try engine.start()
} catch {
    emit(["kind": "error", "message": "Could not start microphone: \(error.localizedDescription)"])
    exit(1)
}

let finalTextLock = NSLock()
var lastFinalText = ""
let recognitionTask = recognizer.recognitionTask(with: request) { result, error in
    if let result {
        let transcript = result.bestTranscription.formattedString
        if result.isFinal {
            finalTextLock.lock()
            let delta: String
            if transcript.hasPrefix(lastFinalText) {
                delta = String(transcript.dropFirst(lastFinalText.count)).trimmingCharacters(in: .whitespacesAndNewlines)
            } else {
                delta = transcript
            }
            lastFinalText = transcript
            finalTextLock.unlock()
            if !delta.isEmpty {
                emit(["kind": "transcript", "text": delta, "final": true])
            }
        } else {
            emit(["kind": "transcript", "text": transcript, "final": false])
        }
    }

    if let error {
        emit(["kind": "error", "message": "Speech recognition failed: \(error.localizedDescription)"])
        exit(1)
    }
}

emit(["kind": "started"])

DispatchQueue.global(qos: .userInitiated).async {
    while let command = readLine() {
        if command == "stop" {
            engine.stop()
            input.removeTap(onBus: 0)
            request.endAudio()
            DispatchQueue.main.asyncAfter(deadline: .now() + 8) {
                emit(["kind": "stopped"])
                exit(0)
            }
            break
        }
    }
}

RunLoop.main.run()
withExtendedLifetime(recognitionTask) {}
