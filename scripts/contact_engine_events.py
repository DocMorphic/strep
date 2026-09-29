"""Authored contact boundaries for study playback, not measured contact claims."""


def contact_events(spec, frame_count):
    """Preserve each explicit region/interval and the supplied clip clock."""
    if type(frame_count) is not int or frame_count < 1:
        raise ValueError('Positive integer frame count required')
    if not isinstance(spec, dict) or spec.get('fps') != 30 or spec.get('frame_count') != frame_count:
        raise ValueError('Contact event clock differs from motion')
    regions = spec.get('regions')
    if not isinstance(regions, dict):
        raise ValueError('Contact regions required')
    events = []
    for region, entry in regions.items():
        if not isinstance(region, str) or not region or not isinstance(entry, dict):
            raise ValueError('Named contact region required')
        mode = entry.get('mode')
        segments = entry.get('segments', [])
        if mode not in ['explicit', 'inferred', 'disabled'] or not isinstance(segments, list):
            raise ValueError('Invalid contact event mode or intervals')
        if mode != 'explicit':
            if segments:
                raise ValueError('Only explicit contacts have authored intervals')
            continue
        if not segments:
            raise ValueError('Explicit contact intervals required')
        previous_end = -1
        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise ValueError('Invalid contact interval')
            start, end = segment.get('start_frame'), segment.get('end_frame')
            if type(start) is not int or type(end) is not int or not 0 <= start <= end < frame_count or start <= previous_end:
                raise ValueError('Contact intervals must be ordered, disjoint and within the clip')
            previous_end = end
            for boundary, frame in [('start', start), ('end', end)]:
                events.append(dict(type='requested_pin_' + boundary, actor='A', region=region,
                                   segment_index=index, frame=frame, time_s=frame / 30))
    events.sort(key=lambda event: event['frame'])
    return dict(fps=30, events=events)
