"""Freeze a broad diagnostic baseline before generation; never a motion whitelist."""
from pathlib import Path
from strep import ROOT, read, save, sha256, source_check, now
from action_requests import validate_batch, request_digest

SEEDS = [1301, 2089, 3253, 4099, 5101]
# ID, duration, primary prompt, required context; optional independently generated partner prompt.
FAMILIES = {
 'locomotion': [
  ('backpedal-check',5,'A person backpedals cautiously for several steps, glances over their left shoulder, then comes to a controlled stop.','floor'),
  ('lateral-cross-step',6,'A person travels to the left using crossing side steps, reverses direction and returns with crossing side steps to the right.','floor'),
  ('tight-circle',7,'A person walks around a tight clockwise circle and stops facing the direction they started.','floor'),
  ('heel-to-toe-sneak',6,'A person sneaks forward slowly, placing each foot carefully heel to toe while keeping their shoulders low.','floor'),
  ('accelerate-brake',7,'A person starts walking, accelerates into a quick jog for several steps, then brakes smoothly to a balanced standstill.','floor'),
  ('pivot-return',5,'A person takes three forward steps, pivots sharply through half a turn on one foot, and walks back.','floor')],
 'parkour': [
  ('broad-jump-stick',5,'A person crouches, swings both arms and makes one long standing broad jump, absorbing the landing and holding their balance.','floor'),
  ('single-leg-hops',6,'A person makes three small forward hops on the right foot, using both arms for balance, then places the left foot down.','floor'),
  ('running-leap',7,'A person takes a short running approach, leaps forward from one foot, lands on the opposite foot and takes two recovery steps.','floor'),
  ('low-vault',6,'A person approaches a waist-high obstacle, plants both hands on its top, vaults their legs to one side and lands beyond it.','obstacle'),
  ('wall-plant-turn',6,'A person runs toward a vertical wall, plants the right foot against it, pushes away and turns to land facing away from the wall.','wall'),
  ('ledge-pull-up',8,'A person hangs by both hands from a high ledge, pulls their chest above it, places a knee on top and climbs up to stand.','ledge')],
 'ground_and_recovery': [
  ('kneel-rise',6,'A person lowers onto both knees, pauses upright on their knees, steps one foot forward and rises to standing.','floor'),
  ('crouch-sideways',6,'A person drops into a low squat and takes four sideways steps while staying low, then stands upright.','floor'),
  ('belly-crawl',7,'A person lies on their stomach and crawls forward using alternating forearm pulls and small pushes from their feet.','floor'),
  ('side-roll-recover',6,'A person lowers to the floor, rolls sideways over their right shoulder and hip, and pushes back up to a kneeling position.','floor'),
  ('cross-legged-rise',8,'A person sits cross-legged on the floor, reaches forward with both hands, draws their feet underneath them and stands.','floor'),
  ('stumble-hand-recovery',5,'A person stumbles forward, catches themself briefly with the left hand on the ground, then pushes back up and regains balance.','floor')],
 'combat': [
  ('jab-cross-retreat',5,'A person in a boxing stance throws a quick left jab and right cross, returns both hands to guard and takes a short step backward.','floor'),
  ('roundhouse-recover',5,'A person pivots on the left foot, swings a right roundhouse kick at waist height, retracts the leg and returns to a balanced stance.','floor'),
  ('guard-duck',5,'A person raises both forearms to protect their head, ducks under an incoming strike and rises back into guard.','floor'),
  ('sidestep-elbow',5,'A person takes a quick sidestep to the right, rotates their torso into a left elbow strike and returns to guard.','floor'),
  ('low-sweep',6,'A person lowers their body, spins into a low sweeping kick close to the ground and rises into a stable fighting stance.','floor'),
  ('sword-parry-riposte',6,'A person holds a sword with both hands, redirects an incoming strike with a diagonal parry, then makes one controlled forward thrust and recovers.','weapon')],
 'gestures_and_expression': [
  ('beckon-left',5,'A person extends their left arm and repeatedly curls their hand toward them in a clear come-here gesture, then relaxes.','floor'),
  ('look-point',6,'A person looks to their right, turns their upper body and points with their right arm toward something high in the distance.','floor'),
  ('hand-to-chest-bow',5,'A person places their right hand over their chest, bows politely from the waist and straightens again.','floor'),
  ('wide-shrug',5,'A person lifts both shoulders and spreads their forearms with palms turned upward in a broad confused shrug, then lowers them.','floor'),
  ('double-fist-cheer',6,'A person reacts with excitement, raises both fists overhead, pumps them twice and settles into a relaxed stance.','floor'),
  ('dismissive-wave',5,'A person leans slightly away and makes a dismissive outward wave with their left hand before turning their head aside.','floor')],
 'dance_and_performance': [
  ('grapevine',7,'A person dances a grapevine step to the left, crossing one foot behind the other, taps, then repeats the pattern to the right.','floor'),
  ('full-turn-balance',6,'A person gathers their arms, makes one full controlled dance turn on the left foot and opens their arms as they finish balanced.','floor'),
  ('heel-toe-shuffle',6,'A person performs a quick heel-toe dance shuffle in place, alternately turning their knees inward and outward with rhythmic arm movement.','floor'),
  ('squat-pulse',6,'A person dances with four low rhythmic squat pulses, shifting their weight from side to side and moving their hands to the beat.','floor'),
  ('waltz-sway',7,'A person performs slow graceful waltz-like steps in a small circle, swaying through the torso and extending their arms softly.','floor'),
  ('robot-popping',6,'A person performs a robotic popping dance with sharply segmented elbow, shoulder and torso motions and brief motionless pauses.','floor')],
 'everyday_tasks': [
  ('tie-shoe',8,'A person bends down, kneels on the right knee, uses both hands to tie the left shoelace, then rises to stand.','floor'),
  ('scratch-head',5,'A person scratches the back of their head with their right hand, stretches their neck gently and lowers the arm.','floor'),
  ('high-shelf-reach',6,'A person reaches both hands toward a high shelf, rises onto their toes to retrieve a small object and brings it down to chest level.','shelf'),
  ('chair-sit-rise',8,'A person turns to align with a chair, sits down carefully, pauses with their back upright and stands up again.','chair'),
  ('sweep-floor',7,'A person grips a long broom with both hands and sweeps the floor with three broad side-to-side strokes while shifting their weight.','tool'),
  ('wipe-window',7,'A person wipes a vertical window with their right hand in large circular motions, reaching higher and then lower.','wall')],
 'object_manipulation': [
  ('lift-ground-box',7,'A person bends their knees and hips, grips the sides of a box on the ground with both hands, lifts it to chest height and holds it steady.','box'),
  ('carry-place-box',8,'A person carries a heavy box in both arms for three careful steps, bends their knees and places the box down gently.','box'),
  ('overhand-throw',5,'A person holds a ball in their right hand, draws the arm back, steps forward and makes an overhand throw with a full follow-through.','ball'),
  ('catch-at-chest',5,'A person tracks an approaching ball, reaches forward with both hands, catches it at chest height and draws it toward their body.','ball'),
  ('push-cart-stop',7,'A person grips a cart handle with both hands, pushes the cart forward for several steps and slows it to a controlled stop.','cart'),
  ('turn-door-handle',6,'A person reaches with the right hand, grasps and turns a door handle, pulls the door open and steps back to clear its path.','door')],
 'partner_interaction': [
  ('handshake',6,'A person reaches their right hand toward another person, grasps the offered hand, shakes it three times and releases.','partner','A person offers their right hand to another person, shares a three-shake handshake and lowers their arm after releasing.'),
  ('hug-separate',7,'A person steps toward another person, wraps both arms around their upper back for a brief hug, releases and steps back.','partner','A person welcomes an approaching partner with open arms, returns a brief hug around their shoulders and steps apart.'),
  ('left-high-five',5,'A person raises their left palm toward another person for a high-five, meets the other palm overhead and lowers their arm.','partner','A person raises their left hand to meet an approaching left palm in an overhead high-five, then lowers the hand.'),
  ('help-partner-rise',8,'A standing person bends their knees, offers both hands to a person seated on the floor and pulls backward steadily to help them stand.','partner','A person seated on the floor reaches both hands toward a standing partner, takes the offered hands and pushes through their legs to rise.'),
  ('pass-box',7,'A person holding a box at chest height extends it toward another person, waits for the other person to take its weight and releases both hands.','partner_object','A person extends both hands to receive a box from another person, takes its weight against their chest and draws it closer.'),
  ('shoulder-bump',6,'A person walks beside a partner, gives them a gentle playful shoulder bump and takes a balancing step away.','partner','A person walking beside another person receives a gentle shoulder bump, sways sideways and takes a step to regain balance.')],
 'environment_traversal': [
  ('stairs-up',7,'A person climbs a short flight of stairs one step at a time, lifting each foot clear of the next riser.','stairs'),
  ('stairs-down',7,'A person walks down a short flight of stairs carefully, bending the supporting knee as each foot reaches the lower step.','stairs'),
  ('uphill-walk',7,'A person walks steadily uphill on a steep slope, leaning their torso forward and taking short deliberate steps.','slope'),
  ('ladder-climb',8,'A person climbs three rungs of a vertical ladder, alternating their hands and feet while staying close to the ladder.','ladder'),
  ('narrow-gap',6,'A person turns their body sideways, shuffles through a narrow gap between two walls and turns forward again.','walls'),
  ('crawl-under-beam',8,'A person crouches, lowers onto hands and knees, crawls beneath a low horizontal beam and stands on the other side.','beam')],
 'aerial_and_nonwalking': [
  ('freestyle-swim',7,'A person swims freestyle horizontally, alternating long arm strokes and steady flutter kicks while turning their head briefly to breathe.','water'),
  ('breaststroke',7,'A person swims a slow breaststroke, sweeping both arms outward and inward together with coordinated frog kicks.','water'),
  ('tread-water',7,'A person treads water upright, sculling with both forearms and making alternating circular leg movements to stay afloat.','water'),
  ('back-float',7,'A person floats on their back in water, spreads their arms gently and makes small relaxed hand movements to maintain balance.','water'),
  ('rope-knee-raise',7,'A person hangs from a rope with both hands, draws their knees toward their chest and slowly extends their legs again.','rope'),
  ('bar-swing',7,'A person hangs with both hands from an overhead bar and swings their body forward and backward by coordinating their hips and legs.','bar')],
 'stylized_and_capability': [
  ('exhausted-walk',7,'An exhausted person trudges forward with heavy slow steps, drooping shoulders and loosely hanging arms, then pauses to recover.','floor'),
  ('agile-zigzag',6,'An agile athletic person moves forward with quick springy zigzag steps, rapidly changing direction while keeping their balance.','floor'),
  ('heavy-turn',6,'A very heavy character takes broad deliberate steps, turns their whole body slowly and settles their weight before stopping.','floor'),
  ('guard-injured-arm',6,'A person protects a sore left arm against their torso while cautiously reaching forward with the right hand and taking a short step.','floor'),
  ('cartoon-joy-hop',6,'An exuberant cartoon-like person makes three exaggerated joyful hops with large arm swings and bouncy recoveries.','floor'),
  ('fearful-retreat',6,'A frightened person recoils, hunches their shoulders, raises their hands defensively and takes several hesitant backward steps.','floor')]
}


def protocol():
    cases=[]
    for family, entries in FAMILIES.items():
        for index,row in enumerate(entries):
            identifier,duration,prompt,context,*partner=row
            actors=[{'id':'A','prompt':prompt}]
            if partner:actors.append({'id':'B','prompt':partner[0]})
            cases.append({'id':family+'-'+identifier,'family':family,'round':index+1,'duration_s':duration,
                          'context':context,'flat_floor_screen_applicable':context=='floor',
                          'actors':actors,'seeds':SEEDS,
                          'scene_validation':'not_required_for_free_space_baseline' if context=='floor' else 'missing_required_context_validation',
                          'human_semantic_review':'required'})
    return {'schema':1,'id':'breadth-baseline-v2','purpose':'Broad frozen diagnostic baseline, not release acceptance or a prompt whitelist',
            'held_out_claim':'New local diagnostic prompts; checkpoint training-set overlap unknown. Not an untouched final release set.',
            'cases':cases,'expected_cases':72,'expected_actor_clips':390,'fps':30,'denoising_steps':100,
            'postprocessing':False,'seeds':SEEDS,'independent_partner_generation':True,
            'missing_context_policy':'Object/partner/environment realism fails to establish support without geometry, synchronized contacts and applicable scene checks. Generating the description alone never passes these requirements.',
            'screens':{'joint_floor_depth_m':.01,'predicted_foot_speed_p95_m_s':.15,
                       'qualification':'Existing diagnostic screens retained; not surface/contact/physical or semantic acceptance. Only apply flat-floor screens to floor-context cases.'},
            'review_policy':'Human ratings and cleanup times stay missing until independently supplied; missing evidence cannot pass.'}


def batches(spec):
    result=[]
    for round_number in range(1,7):
        for suffix,seeds in [('a',SEEDS[:4]),('b',SEEDS[4:])]:
            requests=[]
            for case in spec['cases']:
                if case['round']!=round_number:continue
                for actor in case['actors']:
                    requests.append({'id':case['id']+'-'+actor['id'].lower(),
                        'label':case['id'].replace('-',' ')+' / '+actor['id'],
                        'segments':[{'prompt':actor['prompt'],'duration_s':case['duration_s']}],'seeds':seeds,
                        'scene_requirements':[] if case['context']=='floor' else [case['context']+' context/contact validation required; independent raw skeleton baseline only']})
            batch=validate_batch({'schema_version':1,'requests':requests})
            result.append((f'breadth-v2-round-{round_number:02d}-{suffix}',batch))
    return result


def main():
    output=ROOT/'reports/breadth-baseline-v2'
    if output.exists():raise ValueError('Preserve the frozen study; output already exists')
    spec=protocol();generated=batches(spec)
    output.mkdir();save(output/'protocol.json',spec)
    plan=[]
    for identifier,batch in generated:
        path=output/'requests'/(identifier+'.json');save(path,batch)
        plan.append({'id':identifier,'request':path.relative_to(ROOT).as_posix(),'request_sha256':sha256(path),
                     'request_digest':request_digest(batch),'output':'reports/action-jobs/'+identifier,
                     'reuse_from':None if identifier.endswith('-a') else 'reports/action-jobs/'+identifier[:-1]+'a'})
    save(output/'freeze.json',{'at':now(),'kimodo_commit':source_check(),'source_lock_sha256':sha256(ROOT/'benchmarks/sources.lock.json'),
        'model_manifest_sha256':sha256(ROOT/'models/manifest.json'),'protocol_sha256':sha256(output/'protocol.json'),
        'implementation_sha256':{n:sha256(ROOT/'scripts'/n) for n in ['prepare_breadth_v2.py','run_actions.py','generate_actions.py','action_encoder.py','export_actions.py']},'batches':plan})
    save(output/'pipeline.json',{'status':'prepared','expected_clips':390})
    print(f'Frozen {len(spec["cases"])} cases, {len(plan)} batches, 390 independently generated actor clips')


if __name__=='__main__':main()
