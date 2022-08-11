import music21
import numpy as np
import subprocess
from IPython.display import Image, Audio

START = 'START'
END = 'END'
HOLD = '__'
NC = '<<NC>>'
REST = 'rest'

NOTE_INDICES_CACHE_FILE = 'cache/note_indices.pickle'
NOTE_INDICES_FILENAME = 'cache/note_indices.json'
INDICES_NOTE_FILENAME = 'cache/indices_note.json'

SUBDIVISION = 4


def save(music, filename):
  music.write('lily.png', fp=f'{filename}')
  # music.write('lily', fp=f'{filename}.ly')
  subprocess.run(['rm', f'{filename}', f'{filename}-1.eps', f'{filename}-2.eps', f'{filename}-systems.count', f'{filename}-systems.tex', f'{filename}-systems.texi'])

  midi_file = music.write('mid', fp=f'{filename}.mid')
  # subprocess.run(['timidity', f'{filename}.mid', '-Ow', '-o', '|', 'ffmpeg', '-i', '-', '-acodec', 'libmp3lame', '-ab', '64k', f'{filename}.mp3']) # outputs .mp3
  subprocess.run(['timidity', f'{filename}.mid', '-Ow']) # outputs .wav
  subprocess.run(['ffmpeg', '-i', f'{filename}.wav', '-acodec', 'libmp3lame', '-ab', '256K', f'{filename}.mp3']) # outputs .wav
  subprocess.run(['rm', f'{filename}.mid', f'{filename}.wav'])

  # music.write('mxl', fp=f'{filename}.mxl')
  music.write(fp=f'{filename}.mxl')


def note_to_str(note_or_rest):
  """
  Convert music21 objects to str
  """
  if isinstance(note_or_rest, music21.note.Note):
    return note_or_rest.nameWithOctave
  if isinstance(note_or_rest, music21.note.Rest):
    return note_or_rest.name
  if isinstance(note_or_rest, str):
    return note_or_rest
  if isinstance(note_or_rest, music21.harmony.ChordSymbol):
    return note_or_rest.figure
  if isinstance(note_or_rest, music21.expressions.TextExpression):
    return note_or_rest.content
  

def str_to_note(note_or_rest_str):
  if note_or_rest_str == 'rest' or note_or_rest_str == START or note_or_rest_str == END or note_or_rest_str == HOLD or note_or_rest_str == NC:
    return music21.note.Rest()
  else:
    return music21.note.Note(note_or_rest_str)


def chorale_to_sequence(chorale, offset_start, offset_end, note_indices, indices_note):
  # notes = chorale.parts[0].flat.getElementsByOffset(
  notes = chorale.flat.getElementsByOffset(
      offset_start,
      offset_end,
      classList=[music21.note.Note, music21.note.Rest]) 
  note_strs = [note.nameWithOctave for note in notes if note.isNote]  

  tick_length = int((offset_end - offset_start) * SUBDIVISION)

  for note in note_strs:
    if note not in note_indices:
      new_index = len(note_indices)
      note_indices.update({note: new_index})
      indices_note.update({new_index: note})
      # print(f'New entry {new_index}:{note}')
  j = 0
  i = 0
  t = np.zeros((tick_length, 2), dtype=int)
  is_articulated = True
  num_notes = len(notes)
  while i < tick_length:
    # print(f'{i} {is_articulated}\n{list(t)}')
    if j < num_notes - 1:
      if notes[j + 1].offset > i / SUBDIVISION + offset_start:
        t[i, :] = [note_indices[note_to_str(notes[j])],
                          is_articulated]
        i += 1
        is_articulated = False
      else:
        j += 1
        is_articulated = True
    else:
      t[i, :] = [note_indices[note_to_str(notes[j])],
               is_articulated]
      i += 1
      is_articulated = False
  seq = t[:, 0] * t[:, 1] + (1 - t[:, 1]) * note_indices[HOLD]
  return list(seq)
  

def sequence_to_chorale(sequence, note_indices, indices_note):
  score = music21.stream.Score()
  part = music21.stream.Part(id='part0')
  dur = 0
  f = music21.note.Rest()
  for note_index in sequence:
    if not note_index == note_indices[HOLD]:
      if dur > 0:
        f.duration = music21.duration.Duration(dur / SUBDIVISION)
        part.append(f)

      dur = 1
      f = str_to_note(indices_note[note_index])
    else:
      dur += 1
  f.duration = music21.duration.Duration(dur / SUBDIVISION)
  part.append(f)
  score.insert(part)
  return score


def pitch_with_harmony_sequence(sequence, note_indices):
  chorale_voices = []
  for _ in range(4):
    chorale_voices.append([])
  for token in sequence.split():
    chorale_seq = []
    token_split = token.split(':')

    observed = token_split[0]
    observed_split = observed.split(',')
    harmony_str_1 = observed_split[0]
    harmony_str_2 = observed_split[1]
    harmony_str_3 = observed_split[2]

    hidden = token_split[1]
    hidden_split = hidden.split(',')
    note_str = hidden_split[0]

    chorale_voices[0].append(note_indices[note_str])
    chorale_voices[1].append(note_indices[harmony_str_1])
    chorale_voices[2].append(note_indices[harmony_str_2])
    chorale_voices[3].append(note_indices[harmony_str_3])
  return chorale_voices

def pitch_with_harmony_sequence_non_hidden(sequence, note_indices):
  chorale_voices = []
  for _ in range(4):
    chorale_voices.append([])
  for token in sequence.split():
    chorale_seq = []
    token_split = token.split(':')

    hidden = token_split[1]
    hidden_split = hidden.split(',')
    note_str = hidden_split[0]
    harmony_str_1 = hidden_split[1]
    harmony_str_2 = hidden_split[2]
    harmony_str_3 = hidden_split[3]

    chorale_voices[0].append(note_indices[note_str])
    chorale_voices[1].append(note_indices[harmony_str_1])
    chorale_voices[2].append(note_indices[harmony_str_2])
    chorale_voices[3].append(note_indices[harmony_str_3])
  return chorale_voices




def harmony_sequence_to_chorale(sequence, note_indices, indices_note):
  score = music21.stream.Score()
  for voice_idx in range(len(sequence)):
    part = music21.stream.Part(id=f'part{voice_idx}')
    if voice_idx < 2:
      part.append(music21.clef.TrebleClef())
    else:
      part.append(music21.clef.BassClef())
    dur = 0
    f = music21.note.Rest()
    for note_index in sequence[voice_idx]:
      if not note_index == note_indices[HOLD]:
        if dur > 0:
          f.duration = music21.duration.Duration(dur / SUBDIVISION)
          part.append(f)
  
        dur = 1
        f = str_to_note(indices_note[note_index])
      else:
        dur += 1
    f.duration = music21.duration.Duration(dur / SUBDIVISION)
    part.append(f)
    score.insert(part)
  return score


def get_beat_metadata(sequence):
  new_sequence = []
  beat_counter = 0
  for token in sequence:
    new_sequence.append(beat_counter+1)
    beat_counter = (beat_counter + 1) % SUBDIVISION
  return new_sequence

