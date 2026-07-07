// Business-school-quality content banks for the demo transcripts.
//
// Design: rather than hand-authoring hundreds of flat message strings, each
// assignment gets a bank of CORE sentences per reasoning-move category, plus
// one shared "reason" closer and one shared "specific" (brand/number) closer.
// The generator composes a turn's message from core + (optionally) reason +
// (optionally) specific + (optionally) a bonus sentence from a different
// category + (optionally) a challenge-response phrase. That combinatorics
// produces well over 25 distinct realized messages per assignment while
// keeping quality-tier control precise (heuristicAnalyze's qualityOf() reads
// the whole message: matched pattern + a "since/since" reason marker +
// digit-or-named-brand specificity over 120 chars is what pushes 2 -> 3 -> 4).

export type ContentCategory =
  | "evidence"
  | "assumption"
  | "counter"
  | "perspective"
  | "synthesis"
  | "reflection";

export interface AssignmentContent {
  openRich: string[];
  openPlain: string[];
  core: Record<ContentCategory, string[]>;
  revision: string[];
  reasonAddon: string[];
  /** Must contain a digit, a named brand (Uber/Airbnb/Visa/Amazon/Tesla/Netflix), or "for example"/"e.g."/"such as". */
  specificAddon: string[];
}

// ---------- Shared (assignment-agnostic) challenge-response phrase banks ----------

/**
 * DISAGREE_MARKERS + REASON_MARKERS -> "defended". Deliberately avoids the
 * counterargument-pattern trigger words (however/counterargument/counterexample/
 * critics/one could argue/objection/push back/skeptic) so that "defending"
 * a position doesn't itself inflate the counterargument_use dimension on
 * every challenge turn regardless of the turn's actual content category.
 */
export const DEFEND_PHRASES: string[] = [
  "I still maintain the core claim, since the exception you raise proves the rule rather than refuting it.",
  "Even so, my point stands: that shows variance in outcomes, not that the underlying mechanism is wrong, since the mechanism is a tendency, not a law.",
  "Nevertheless, I disagree that this undermines the thesis, since the cases where it fails share a specific precondition that isn't present in the general case I'm arguing.",
  "I stand by the claim regardless — it doesn't depend on every case going the same way, since I'm describing a tendency, and a handful of exceptions doesn't erase a tendency.",
];

/**
 * CONCESSION regex + REASON_MARKERS -> "adapted". Same care taken to avoid
 * counterargument-pattern trigger words beyond the intended concession ones.
 */
export const ADAPT_PHRASES: string[] = [
  "I'll concede that point — it's a strong one, and it means I need to narrow my claim rather than abandon it, since a blanket position clearly overreaches.",
  "Granted, that's a fair point; admittedly the original claim was too absolute, since what you're pointing to genuinely cuts against the strongest version of it.",
  "That's true, and I accept the challenge — the claim holds only in the narrower case I originally had in mind, since the general case is clearly more contested than I treated it.",
  "Fair point, I'll grant that much; the claim needs a qualifier here, since without one it's asserting more than the case actually supports.",
];

/** Must start with yes/true/good point/agreed/okay, no reason marker -> "accepted_bare" */
export const ACCEPT_BARE_PHRASES: string[] = [
  "Good point, I hadn't thought about that.",
  "Yes, that's fair.",
  "Okay, I agree with that.",
  "Agreed, that makes sense.",
];

/** No disagree/reason/concession markers, changes the subject -> "ignored" */
export const IGNORE_PHRASES: string[] = [
  "Moving on, I want to add one more thing about the assignment.",
  "Anyway, let me go back to my main point about the case.",
  "Right, so building on my point a bit further.",
  "Okay well, going back to what I was saying before.",
];

// ---------- A1: Platform competition ----------

const A0: AssignmentContent = {
  openRich: [
    "My position is that first-mover advantage in platform markets is sustainable, but only when it is reinforced by strong network effects and rising switching costs — otherwise the leader is just occupying space a faster follower can take.",
    "I'll argue that platform leadership persists when — and only when — the incumbent has solved the two-sided chicken-and-egg problem in a way a challenger cannot cheaply replicate; being first is necessary but nowhere near sufficient.",
  ],
  openPlain: [
    "I think first-mover advantage in platforms can be sustainable, since the first company usually gets more users early.",
    "My view is that being first in a platform market should help a lot, since more users tend to join the biggest platform.",
  ],
  core: {
    evidence: [
      "Historically, platform leaders that lock in supply-side participants early have compounded their advantage through network effects, as new users make the platform marginally more valuable to existing ones.",
      "Research on two-sided markets suggests that the platform able to solve the chicken-and-egg problem first tends to accumulate a durable data and liquidity advantage over any later entrant.",
      "According to the platform economics literature, switching costs rise mechanically as users accumulate history, reviews, and social graph on one side of the market.",
      "Historically, the platforms that survive a challenger's entry are the ones where supply-side participants have something to lose by leaving, not just users with a login to abandon.",
    ],
    assumption: [
      "That argument assumes the switching cost stays constant, which may not hold if a regulator forces platforms to make user information portable.",
      "This only holds if users actually experience meaningful friction when trying a second app — an assumption that's shakier every year as most people run several competing apps at once.",
      "There's a premise underneath this claim that supply-side participants can't easily serve two platforms at once, and multi-homing behavior suggests that premise is increasingly fragile.",
      "The whole argument depends on whether network effects are strong enough to outweigh price competition, and that's not something the analysis can simply presuppose.",
    ],
    counter: [
      "However, critics of the sustainable-moat view would point out that multi-homing is now the default behavior in most consumer categories, which erodes any single platform's lock-in.",
      "One could argue that first-mover advantage is actually a liability in platform markets, since the second mover can watch what fails and design around it.",
      "A skeptic would push back that network effects are frequently overstated, and that most of the observed advantage is really just superior execution, not the network itself.",
      "Critics would raise the objection that regulation increasingly targets exactly this kind of lock-in, so treating it as permanent ignores a live policy risk.",
    ],
    perspective: [
      "From a regulator's vantage point, however, the sustainability of that advantage looks less like innovation and more like a barrier to entry that deserves scrutiny.",
      "A new entrant would push back that the incumbent's advantage is really about capital access, not network effects, and that a well-funded challenger can buy its way to relevance.",
      "From a supply-side participant's vantage point, however, staying loyal to one platform only makes sense as long as that platform keeps outperforming the alternative — loyalty is conditional, not structural.",
      "A customer with real alternatives would push back that they multi-home constantly already, which suggests the lock-in story is stronger in theory than in their actual daily behavior.",
    ],
    synthesis: [
      "Taken together, this suggests my refined position: first-mover advantage is sustainable only where switching costs and network effects reinforce each other, not wherever a platform simply arrived first.",
      "Putting this together, therefore my position is that durability comes from compounding data and habit, not from the calendar date a platform launched.",
      "Overall, combining the mechanism and the counterexamples, my refined thesis is conditional: sustainable if the moat compounds, fragile if it's just a head start.",
      "In sum, my position going forward is that the interesting question was never 'first or not' but which specific mechanism is doing the locking-in work.",
    ],
    reflection: [
      "Looking back at this discussion, I notice my reasoning leaned hard on the success stories and I was too quick to treat survivorship bias as if it were a natural law of platform markets.",
      "Reflecting on this, I realize I kept reaching for the same two or three examples, and my reasoning would be more honest if I actively looked for platforms that were first and still lost.",
      "I notice that my confidence was highest exactly where I had the least evidence — I tend to treat a plausible mechanism as if it were a proven one.",
      "Looking back, my reasoning treated users as behaving rationally about switching costs, when actually habit and inertia probably explain as much of the pattern as the economics do.",
    ],
  },
  revision: [
    "I'm revising my position: I now think sustainability depends on the specific mechanism at work, not on being first, so I no longer think the thesis can be a flat yes or no.",
    "Updating my view, instead I now think 'sustainable' should be a spectrum tied to switching-cost strength, not a binary property of being early.",
    "I was wrong to treat this as a single claim — revising it, I now think there are really two different questions bundled together here, and they have different answers.",
  ],
  reasonAddon: [
    "That matters since the mechanism keeps compounding only as long as users have a real reason not to switch.",
    "This is worth taking seriously since the argument only holds while the underlying behavior — sticking with one app — actually continues.",
    "That's an important qualification since platform dynamics tend to be case-specific rather than universal.",
    "This is worth flagging since the strength of the effect varies enormously by category, from ride-hailing to payments to social media.",
  ],
  specificAddon: [
    "Visa, for example, still clears the large majority of card-present volume decades after rivals entered, precisely since both merchants and cardholders are locked into one rail.",
    "Airbnb kept its host base even as Vrbo copied the listing model, since migrating a superhost's reviews and calendar to a new app destroys the very asset that makes them a superhost.",
    "Uber and TikTok both show the opposite pattern: each overtook an established incumbent within a few years by competing on a different mechanic rather than the existing network.",
  ],
};

// ---------- A2: Disruption & incumbents ----------

const A1: AssignmentContent = {
  openRich: [
    "My position is that well-managed incumbents fail since their profit-maximizing logic is working exactly as designed — and that the failure is avoidable only if leadership deliberately overrides that logic for a specific unit.",
    "I'll argue that disruption is not a failure of foresight but a failure of organizational structure, which makes it avoidable in principle but genuinely rare in practice.",
  ],
  openPlain: [
    "I think incumbents fail since they don't pay enough attention to new competitors until it's too late.",
    "My view is that big companies fail against disruption mostly since they get too comfortable with their existing customers.",
  ],
  core: {
    evidence: [
      "Historically, incumbents facing disruptive entrants have under-invested in the new technology since it looked unprofitable relative to their existing customer base.",
      "Research on disruptive innovation suggests that the resource allocation process inside large firms systematically favors sustaining investments over disruptive ones.",
      "According to the innovator's dilemma literature, the very listening-to-customers discipline that makes incumbents excellent also makes them blind to a market that doesn't exist yet.",
      "Historically, the products that eventually disrupt an industry start out worse on every dimension the incumbent's best customers care about, which is exactly why incumbents dismiss them.",
    ],
    assumption: [
      "That argument assumes the incumbent's existing customers are representative of the market that matters, which only holds if the low end of the market never becomes good enough to serve the mainstream.",
      "This depends on whether the new technology actually improves fast enough to cross into the incumbent's core market — a premise that isn't guaranteed for every disruptive-looking entrant.",
      "There's a premise here that management actually had the information needed to see this coming, and in some cases the signal was far weaker than it looks in hindsight.",
      "The whole claim assumes 'well-managed' and 'doomed' aren't in tension, which is a premise worth testing rather than just taken for granted.",
    ],
    counter: [
      "However, critics of the inevitability view would point out that some incumbents do respond in time by acquiring or spinning out a disruptive unit before it threatens the core business.",
      "One could argue that the failure is entirely avoidable, since the technology and the market signal were both visible years before the disruption actually hit.",
      "A skeptic would push back that blaming 'good management' lets executives off the hook for choices that were, in fact, choices.",
      "Critics would raise the objection that plenty of incumbents in the same industry saw the same signal and only some of them failed, which undercuts a purely structural explanation.",
    ],
    perspective: [
      "From a customer's vantage point, however, the incumbent's caution looks less like discipline and more like neglect of a segment they've decided isn't worth serving.",
      "A regulator would push back that letting one incumbent dominate a category for decades, then fail suddenly, is itself a market-structure problem worth examining.",
      "From an employee's vantage point, however, the internal argument to protect the disruptive unit usually loses precisely since the people making the case have less power than the ones defending the core business.",
      "A new entrant would push back that 'the incumbent couldn't have known' is generous — the entrant, after all, was reading the exact same signals and reached a different conclusion.",
    ],
    synthesis: [
      "Taken together, this suggests my refined view: incumbent failure is explained by rational resource allocation under sustaining-innovation logic, and it is avoidable only if leadership deliberately protects a disruptive unit from that logic.",
      "In sum, therefore my thesis is that disruption isn't a failure of foresight but a failure of organizational structure, which is a solvable problem in principle.",
      "Putting this together, my refined position is that the mechanism is structural, not a matter of individual competence — which is actually the more useful and more testable claim.",
      "Overall, combining the theory and the counterexamples, my position is that avoidability is real but rare, since it requires overriding incentives that are working exactly as designed.",
    ],
    reflection: [
      "Reflecting on this discussion, I realize my reasoning kept picturing rational actors making the same choice I would, when actually the interesting question is why smart people reliably make the choice that looks wrong in hindsight.",
      "Looking back, I notice I treat 'the company should have seen it coming' as an argument, when actually seeing something coming and acting on it under uncertainty are very different skills.",
      "I tend to judge these decisions with information the executives didn't have at the time, and reflecting on that, my reasoning owes these cases more charity than I initially gave them.",
      "Looking back at my own argument, I was too quick to treat 'well-managed' as a fixed label, when it's really a description of a system optimized for a market that's about to change underneath it.",
    ],
  },
  revision: [
    "I'm revising my position: instead, I now think the more precise claim is that failure is avoidable in principle but rare in practice, so I was wrong to treat 'avoidable' as if it were 'easy'.",
    "Updating my view, I no longer think 'well-managed' and 'destined to fail' are contradictory — revising the claim, they're actually the same mechanism seen from two angles.",
    "I was wrong to focus only on the technology; revising my position, I now think the organizational incentive structure is doing most of the explanatory work.",
  ],
  reasonAddon: [
    "That matters since the same logic explains both why incumbents miss disruption and why some manage to catch it in time.",
    "This is worth taking seriously since 'well-managed' and 'doomed to fail' are not actually contradictory once you see the mechanism.",
    "That's an important qualification since the outcome depends heavily on how the organization is structured to respond, not just on strategy documents.",
    "This is worth flagging since treating every case the same way hides the cases where deliberate structural choices actually worked.",
  ],
  specificAddon: [
    "Netflix, for example, survived its own technology transition from DVD to streaming, in part since that original business was never profitable enough to be worth protecting.",
    "Kodak invented the first digital camera in 1975 and still filed for bankruptcy in 2012 — seeing a disruption coming and acting on it in time are evidently two different things.",
    "Blockbuster's late, stores-first response to Netflix, versus Amazon's aggressive later entry into streaming, are about as close to a natural experiment as we get for this question.",
  ],
};

// ---------- A3: Venture scaling ----------

const A2: AssignmentContent = {
  openRich: [
    "My position is that aggressive scaling is justified only once unit economics are proven and the competitive window is closing fast — never as a default growth strategy.",
    "I'll argue that the real skill in venture scaling is sequencing: prove the model small, then scale it hard once it's proven, rather than scaling in order to find out whether it works.",
  ],
  openPlain: [
    "I think scaling fast can be the right call sometimes, since if you wait too long a competitor might take the market first.",
    "My view is that startups should be careful about scaling too early, since spending a lot of money before the business works is risky.",
  ],
  core: {
    evidence: [
      "Historically, ventures that scaled headcount and spend ahead of a repeatable unit economics model have burned through their runway before finding one.",
      "Research on venture failure suggests that premature scaling — not product-market fit itself — is the single largest predictor of a startup running out of cash.",
      "According to the venture-scaling literature, the discipline of proving payback period and retention before scaling paid acquisition is what separates durable growth from a growth mirage.",
      "Historically, the companies that scale successfully tend to have already found a repeatable motion in one market or segment before spending heavily to expand it.",
    ],
    assumption: [
      "That argument assumes capital will remain available on demand, which depends on whether the funding environment is still open when the company needs its next round.",
      "This only holds if the competitive window is actually closing as fast as the founders believe, and founders are famously poor judges of their own urgency.",
      "There's a premise here that unit economics measured early are a reliable signal, when early cohorts often behave nothing like the broader market the company is trying to reach.",
      "The whole claim assumes that speed and quality trade off cleanly, which may not be taken for granted once you account for the operational debt that fast scaling creates.",
    ],
    counter: [
      "However, critics of the go-slow view would point out that in a genuine winner-take-most market, moving deliberately just hands the network effect to a faster-moving rival.",
      "One could argue that premature scaling is the wrong diagnosis entirely, and that most of these companies actually failed on product-market fit, not on the pace of spending.",
      "A skeptic would push back that unit economics measured too early are unreliable, so waiting for a clean payback signal can itself be a fatal delay.",
      "Critics would raise the objection that 'prove it small first' is easy advice in a slow-moving category and terrible advice in a market where the winner is decided in eighteen months.",
    ],
    perspective: [
      "From an investor's vantage point, however, the caution looks less like discipline and more like leaving the market to a faster-moving competitor.",
      "A new hire joining a hypergrowth startup would push back that the internal chaos of fast scaling is a cultural cost that the unit-economics argument doesn't capture at all.",
      "From a competitor's vantage point, however, a company that waits to scale until unit economics are perfect is signaling exactly when it's safe to move in and take the market.",
      "A board member would push back that 'wait until it's proven' sounds prudent right up until the round that would have funded the proof never gets raised.",
    ],
    synthesis: [
      "Taken together, this suggests my refined position: aggressive scaling is justified only once unit economics are proven and the competitive window is closing fast — not as a default strategy.",
      "In sum, therefore my thesis is that the real skill is sequencing — proving the model small, then scaling it hard once it's proven, rather than scaling to find out.",
      "Putting this together, my refined view is that the failure mode isn't speed itself, it's speed applied before the underlying model has been validated.",
      "Overall, combining the theory and the counterexamples, my position is that the decision is really a bet on how long the window stays open, made under real uncertainty.",
    ],
    reflection: [
      "Looking back, I notice I tend to reach for the growth-at-all-costs story first, and reflecting on it, that's probably since it's the more dramatic narrative, not since it's the more common one.",
      "Reflecting on this discussion, I realize my reasoning treated 'scaling' as one decision, when it's actually a dozen smaller decisions about hiring, spend, and geography that can each be paced differently.",
      "I notice my confidence was highest when I was talking about famous failures, and looking back, that's survivorship bias again — I don't have good visibility into the quiet cases that scaled fast and it worked.",
      "Looking back at my own argument, I was too quick to treat capital efficiency as always virtuous, when in a truly winner-take-most market it can just mean losing slowly instead of quickly.",
    ],
  },
  revision: [
    "Updating my view: I now think the right frame isn't fast-versus-slow scaling at all, instead it's whether the evidence threshold for scaling has actually been met.",
    "I'm revising my position — instead of a general rule, I now think this has to be answered case by case, against how contested the specific market actually is.",
    "I was wrong to treat capital efficiency as the main variable; revising my thesis, I now think market structure is doing more of the work than spending discipline.",
  ],
  reasonAddon: [
    "That matters since the timing of the decision, not the decision itself, is usually what separates the successful case from the cautionary tale.",
    "This is worth taking seriously since unit economics and growth rate interact, so the right pace depends on both at once.",
    "That's an important qualification since the same action — spending aggressively — is either brilliant or fatal depending on conditions that are hard to observe in the moment.",
    "This is worth flagging since founders rarely get a clean read on the counterfactual of having scaled slower.",
  ],
  specificAddon: [
    "Airbnb's 2020 retrenchment, cutting roughly a quarter of staff to refocus on retention, is exactly the kind of correction a company scaling too fast eventually has to make.",
    "Clubhouse, for example, never made that correction, and its user base fell by more than 90% within about a year of its peak.",
    "Fast raised over a hundred million dollars and still shut down within four years, a clean example of scaling spend faster than any evidence of durable demand.",
  ],
};

export const ASSIGNMENT_CONTENT: AssignmentContent[] = [A0, A1, A2];

/** Which other category a "bonus rigor" sentence should be drawn from, per primary category. */
export const BONUS_PARTNER: Record<ContentCategory | "open", ContentCategory> = {
  open: "counter",
  evidence: "counter",
  counter: "evidence",
  perspective: "evidence",
  synthesis: "counter",
  reflection: "reflection",
  // Never actually used (composeMessage excludes bonus content on assumption
  // turns to keep assumption_testing capped), but Record needs every key.
  assumption: "evidence",
};

/** Faculty-review comment banks, one per persona archetype, referencing the assignment title. */
export const REVIEW_COMMENTS: Record<string, (assignmentTitle: string) => string> = {
  "independent-strong": (t) =>
    `Strong, self-directed work on ${t.toLowerCase()} — volunteers evidence and counterarguments before being asked and holds the line under challenge. A model transcript for the seminar.`,
  "scaffolded-achiever": (t) =>
    `The analysis of ${t.toLowerCase()} is genuinely good, but nearly every substantive move follows a scaffold prompt. Worth an unassisted follow-up to see if the depth travels without the AI's help.`,
  developing: (t) =>
    `Still building the basics on ${t.toLowerCase()} — claims are asserted rather than defended and challenges are accepted without much pushback. Recommend a structured office-hours session.`,
  improver: (t) =>
    `Noticeable growth across the course; the reasoning on ${t.toLowerCase()} is markedly sharper than earlier work and shows the student is starting to test their own assumptions unprompted.`,
  contrarian: (t) =>
    `Consistently the strongest counterargument work in the cohort on ${t.toLowerCase()} — enjoys defending a position, though could stand to volunteer more evidence rather than pure rebuttal.`,
  "steady-mid": (t) =>
    `Solid, middle-of-the-cohort engagement with ${t.toLowerCase()}. Competent but rarely pushes past what the AI's questions prompt — a good candidate to nudge toward more initiative.`,
};
