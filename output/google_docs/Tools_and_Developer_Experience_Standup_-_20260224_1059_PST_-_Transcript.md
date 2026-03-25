---
title: "🛠️📆 Tools and Developer Experience Standup - 2026/02/24 10:59 PST - Transcript"
id: 1jHM5k4I4Wyl6XbvR0qUdPt_CgHU2PVbafh40KZCQdhs
modified_at: 2026-02-24T20:22:41.947Z
public_url: https://docs.google.com/document/d/1jHM5k4I4Wyl6XbvR0qUdPt_CgHU2PVbafh40KZCQdhs/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

## **🛠️📆 Tools and Developer Experience Standup - 2026/02/24 10:59 PST - Transcript**
# **Attendees**
Francisco Liberal, Office TV Robot, Renato Byrro, Teal Larson, Valerie's Sybill Assistant
# **Transcript**
Renato Byrro: Hello T. Is it T or T? Okay.
Teal Larson: E, hold on one second.  I'm the next. Open my laptop and take out my headphones.
Teal Larson: Yeah, it's Christmas.  Despite your surprise, we feel like this needs  Are you able to hear me? Yes.
Renato Byrro: I'm hearing you.
Renato Byrro: I'm not hearing you very well. I'm not sure if it's because of my connection perhaps.
Teal Larson: very well.
Teal Larson: I'm not sure if it's because of the Weird. Okay, hold on. Let me see if I can find headphones.
Teal Larson: There we go.  Why?
Office TV Robot: I see. Hello. Maybe. Cool. Wait,…
Office TV Robot: Tal, you sound like a robot of some sort.
Renato Byrro: Hello.
Renato Byrro: I thought he was my connection. It's raining a lot here. Connection is not very good.
Office TV Robot: …
Office TV Robot: this is where we talk about Whip. Everyone's here today.
Renato Byrro: Francisco, I think someone caught fire.
Office TV Robot: The conversation I don't want to have.
Renato Byrro: Something caught fire in your room. You might want to put out the fire.
Francisco Liberal: Yeah, it's been always burning. Is the world returning?
Renato Byrro: Not anymore.
Office TV Robot: Yes. you sound great.
Francisco Liberal: I didn't start a fire. Yeah.  No.
Teal Larson: Do I still sound like a robot?
Teal Larson: That's so weird. Google really does not like if you change your audio source after joining the meeting.  What could go wrong?
Office TV Robot: When you realize it's JavaScript running your audio connection, I guess that seems So, I want to talk about work in progress limits.  We haven't had our whole group together yet since we talked about this, but this was necessitated primarily by the platform team, but I think it applies to us too. Did you know that for a team of four people, we have 11 in prog in progress projects, two actively being deployed and five being planned? That's not That's probably too many things. so the theory behind work in progress limits is that for a team of four people, we should probably only be actively working on three things at once. Planning one or two things and deploying and waiting should be basically zero as much as it possibly can.
Office TV Robot: we have been a team that historically has been individual focused. Eric Ronaldo will do something. And that's okay for most of the time, but that means that it's really hard to prioritize reviewing somebody's work or their plan. It's really hard to prioritize helping someone get unblocked. so work in progress limits are a kaizen or a conbon process that roughly always work right to left and so if you're finished with whatever you're doing don't start the next thing you finish the waiting thing then help out who's in progress then eventually once the stack is smaller we can plan the new thing
### 00:05:00
Office TV Robot: So, for example, if Francisco was to finish Windows paper cuts, he shouldn't immediately go on to the next thing. He should probably dogpile on Office 365 tools or Salesforce cleanup, whatever is in flight that can be helped. T and I have also been talking about how her work is kind of different and probably won't fit into this kind of plan. but for the rest of us, we should still try to account for this kind of thing. so the way we'll do standups going forward is rather than going around the room saying we're working on, we're going to instead guide it on the projects that are in flight. so we're going to go through the waiting ones first in progress ones. and do our progress that way.
Office TV Robot: And so, for example, if this project is blocked, we should all be working on this before moving on to the next things. and we'll get our standups out that way. traditionally, this type of thing is done at the story level, not the project or epic level. but we are mature, we are very senior, we are excellent people. We don't need to micromanage that deeply, and frankly, I don't want to. so we're going to keep this at the project level for now to start. Eric's seen this happen with the platform team for when you stand up now already as well. What did I forget to share? so maybe you can talk a little bit more about the inrogress limits make sense. is there a planning limit? Is there a deploying limit?
Office TV Robot: how should we think about that? Yeah, I think so. Historically the main pro limit you cared about was the in progress limit because you spent more time implementing than anything else, more time writing code. That might not be true anymore and it might be the fact that we're going to spend more time planning and that is where the cross collaboration will matter the most. we'll be talking to product, we'll be talking to marketing, we'll be talking amongst ourselves about the right way to do something and how agent we want to make it or how deep we want to go with a test suite or guard rails or something. I think planning will eventually become our biggest category and we'll have to figure out the limits there as we go. I know it should always be less than the number of people that there are on the team. So nothing should be bigger than three.
Office TV Robot: And Renado and his 40 product management, I think this will be the largest area of interest once we get there. But we have to make this column shorter first before we can plan anything new. there's 2.2 projects per person in progress and that's not right. Yeah. one thing that I'm curious about, if something is in review, should I have it in progress or deploying waiting? great question. I think in review there's a nuance here that I'm trying to figure out how to explain. in review is probably deploying waiting. let's say that as a starting point. Yeah, I know TL I'm sorry.
Francisco Liberal: How can
Office TV Robot: Please add more. Let's get this accurate first. So, if you can find a project that's not on here, please put it on.
Teal Larson: Should I just put any project that is assigned to me the projects that show up as mine on the timeline? Should I just be tagging all of those tools in DX?
Office TV Robot: Yes, please. Let's get the list accurate to start and then we can discuss…
Teal Larson: Okay.
Office TV Robot: what to do about it. Ronaldo, what's up?
Renato Byrro: I think we're going to need to perhaps break down projects. For example, the Microsoft one had a bunch of MCP servers and I had one milestone for One Drive and Word and another one for PowerPoint and another one for Excel.  and each of them went through planning, execution and review and deploy independently.  So in this new model of tracking work in progress I think we would need separate projects right so we can track their status separately
### 00:10:00
Office TV Robot: Maybe I think it would have been okay to do either. if this project is still in progress because not everything is done yet, somebody can come help help you with the work that is possible. but you could have also said PowerPoint is totally done and Excel is totally done, but everything else isn't. that's also okay. at the story level, it is usually best to have really small individual units of work that can be delivered. I actually don't know at the project level. I have a vibe that tells me I think you're right.
Renato Byrro: Okay.
Office TV Robot: We probably should have broken this one up, but it's I don't know as a rule.
Office TV Robot: Yeah. One thing is how do we avoid making mega projects to stay under our work progress limits? We need to be cognizant of that. Yeah, that's a good argument for splitting them up, too. Yeah.  That's stand up so far.
Francisco Liberal: And how can you decide …
Francisco Liberal: if I see we see the projects how you decides to help what do you offer reviews on those kind of things? So yeah, you have some project in progress rights that you need first offer help but might be that not always our help will be useful. So that will be also fine right?
Francisco Liberal: So you move for the next. Okay.
Office TV Robot: Correct.
Office TV Robot: And it's most interesting when somebody becomes free. So it's very possible that you're working on Ideal Docs for Windows. it's a oneperson job and you've got it covered.  that's fine. But it's very interesting then when Bernado is done with his work and is trying to figure out what to do next. So is there something he can help you move faster? Is there some work that can be parallelized? We'll discuss it at standup and if there is he should do that before doing the next thing.
Office TV Robot: But I certainly believe there's work that is single player. Let's call it that will probably exist for a while. So let's give it a shot. So Teal, you're first.
Office TV Robot: What is remaining to do on this project?
Teal Larson: Yeah, I should circle back and…
Teal Larson: talk to marketing again. It's blocked because nobody has access to delete the ghost account.
Teal Larson: I think it was created by Jamie maybe. I don't know who's following up on deleting whatever subscription exists there. I can delete the content but not the account.
Office TV Robot: I might be able to do that.
Office TV Robot: I will try.
Teal Larson: Great. Glad we had the stand up.
Office TV Robot: It's already working.
Office TV Robot: we can move that to Adio is complete. Great. Wonderful. Ranatada tell us about cough 265.
Renato Byrro: We have two things running. We have the marketing materials. I sent Shy the blog and demo video recording. I will wait for her feedback on them.  And I'm now applying the stuff we centralized in Microsoft utils utilities to the old old MCP servers Outlook and Teams Outlook mail calendar and Microsoft Teams.
Renato Byrro: This is just for standardization sake because there are some things that we implemented in this Microsoft utilities package that is shared by one drive, word excel, powerpoint and sharepoint and now we want to apply the same centralization design to the older MCP servers as well so that we have all of Microsoft MCP servers standardized using the same reusing the same objects and…
Office TV Robot: Makes sense.
Renato Byrro: so I'm doing this now and that's it about Microsoft Office.
### 00:15:00
Office TV Robot: One thing I'll start reminding everyone to do too is we're not going to put dates on a new project until it becomes in project in progress. we've been giving kind of a false signal to the rest of the business about our due dates and stuff because we don't spend the time to estimate as rigorously which we should not do. But once you start working on them, you might have a good guess of how long it'll take.
Office TV Robot: And so, Renado, it's probably not going to be done February 13th because that was in the past. when do you think this project will be done?
Renato Byrro: The MCP servers are ready.
Renato Byrro: The marketing materials I don't know when Shane is planning on launching them. I would need to check with her. And the Microsoft would use centralization I believe one or two more days to finish it and then some one review and then we deploy the new servers. the broad deployment has been a little bit confusing because now we have everything centralized.
Renato Byrro: So I've been bugging everyone to get Excel in production for a few days now. It doesn't depend only on me. So it Excel is still not in production despite being I think it has been merged for more than a week now.
Office TV Robot: Y yes.
Office TV Robot: That is this project to sort that out by the way to let us deploy without the engine being done.
Renato Byrro: Yeah, that would be great.
Renato Byrro: because it would make it easier for us to get things done. I mean, Excel is done, but it's still not in production, so it's not done.
Office TV Robot: Yep, that is…
Office TV Robot: what this category is for, that type of problem is when you end up in this waiting category. let's we'll say by the end of the week and hope for the best. I think theres go to the issues.  I think there's two left in review. so the open- source optimized tools still need a review for adding metadata to them. there's actually another one there in the open source repo about just hardening the extras JSON that's provided just to make sure it's like correct JSON, I guess.
Office TV Robot: and then the skill to add to the monor repo as well is in review. there's also a quick followup for filtering tools by metadata. So if you want to list tools, you can filter and find all here all non-destructive. So I created its own project. it's called filter tools by metadata. It's probably not in progress. so I'm kind of treating it as a mini project. I already have a project plan for it. and on the download Opus one-shotted it as well with the project plan. but I just want Nate to have eyes on it because during that synchronous meeting he said that he wanted to take a look. Yeah. so I'm just going to leave that in the planning stage.
Office TV Robot: I worked on that yesterday and going to kind of put that on the back burner while I work on my other things. so I think we can say that tool tags and categories static project can be in deploying waiting. Love it. Just give me a second but doesn't matter. I think I already added the dependency. Perfect. Also, this is an awesome project and I love that we keep discovering more things. I do have one question about this for Francisco, you added the list tools metadata and private endpoint in the engine.
Office TV Robot: Would you like me to add the ability to filter on tool metadata to that endpoint?
Francisco Liberal: I think for the moment no only…
Francisco Liberal: if Sio wants to use it because I told S that you have it and he might want to take a look on that. and I was taking a look in what you send me. I'm just update the documentation in the tests for what you added for that edit. I think right now that that's fine. That would be needed at least for the documentation generator.
Office TV Robot: Okay, I'll keep it out of scope then.
### 00:20:00
Francisco Liberal: Okay, I'll just get up here with the documentation and…
Francisco Liberal: test updates for that. So you can take a look as well.
Office TV Robot: Okay, because you want this to be a fast ball,…
Office TV Robot: I'm moving this up the list. Feels right. Okay, cool. Francisco, let's talk about Windows.
Francisco Liberal: Yeah, the PR
Francisco Liberal: the first round of review for Eric is done. Now I sent back for reviewing the documentation.
Office TV Robot: 
Office TV Robot: Yeah. I'll give you the second round of review today.
Francisco Liberal: And what I was working right now is we have that documentation project but I think that would be needed because the whole thing that I have is just a documentation how to install with UV and without UV some concerns that might happen in the PowerShell like allowing the scripts and I think that's basically done will be it's just a page I think that extensive really looking into it. I think what necessary.
Francisco Liberal: So yeah, I think that for Windows that there is nothing a lot of things besides those paper cuts and…
Office TV Robot: Do you want to delete this product?
Office TV Robot: Is that what you're suggesting? I love deleting projects.
Francisco Liberal: a small documentation just guiding people how to do a star with UV and those kind of things and set to path and how to do it without UV and with UV. I think that that's basically done. So I think that this project can be deleted only. Yeah.
Office TV Robot: Okay, so we're going to move this to  And then we're going to put in here about Windows specific docs. Paste. And you said this is done already.
Francisco Liberal: Yeah, it's basically done because while I was running I had also in the agent they say if you find something outstanding or something please add here and at the end I had a documentation that I just could structure into kind of steps for Windows.
Francisco Liberal: So I think that's I just create a PR for that. Yeah.
Office TV Robot: But it's not live on the docs website yet.
Office TV Robot: Okay, And then I think all the other tickets here are in the single PR, that I'm reviewing. So those can all go in review. I guess sub issue of insure.
Francisco Liberal: Okay.
Office TV Robot: Okay, Excellent. Wonderful. Okay, Salesforce Ronaldo.
Renato Byrro: I was looking at this earlier today in linear.
Renato Byrro: What is this about? Yeah, I Yeah,…
Office TV Robot: I don't know.
Office TV Robot: It came from whatever this is.
Renato Byrro: I looked into this notion, but I was like, what is this kicking off?
Renato Byrro: The notion page says kickoff. Yeah.
Office TV Robot: I don't know
Teal Larson: I would guess like a P that they're doing with a customer.
Office TV Robot: 
Office TV Robot: who created this. I think.
Office TV Robot: …
Renato Byrro: Yeah. No,…
Office TV Robot: this is great.
Renato Byrro: nobody talked to me about this. Not that I remember. It says in progress, but I have not started anything about it. I mean, I'm working on Salesforce, but it's related to Open Table PC.
Renato Byrro: It's not related to these amaze whatever this is.
Office TV Robot: Perfect. This is exactly…
Office TV Robot: what we should be talking about right here.
Office TV Robot: So, the open table CLC, we understand we
Renato Byrro: Yeah, it's not a cleanup.
Renato Byrro: It was an expansion because the Salesforce C MCP server was very limited. It had only three tools and they were all read only. So, nobody was able to update a lead for example, record a call, create a task,…
Office TV Robot: Oops.
Renato Byrro: things like this.
Renato Byrro: So I added a bunch of tools that allows to retrieve information more specifically. Before we had this god class that retrieves information about an account and then it leads, contacts, tasks, everything in a single tool call which is ended up being great for a lot of use cases for CRM agentic usage.  But sometimes you want to know something specifically about one contact, one lead, one task. And then it's important to have tasks dedicated to reading information from one particular object. and also to update those objects. So this is what I have worked at last week and it's up for review now.
### 00:25:00
Renato Byrro: There are I think 13 or 14 extra tools in the server and today Open Table signaled that they wanted three tools to allow their agents to interact with Salesforce by writing soql queries. it's a variation of SQL created by Salesforce to interact with their data through SQL queries and Guru and I argued against it because it exposes too much complexity for the agent to handle.
Office TV Robot: Right. Okay.
Renato Byrro: We think especially the update one is very risky.
Renato Byrro: I mean you let your agent write SQL queries to edit your entire Salesforce database. I'm not very confident on doing this. So we might include other things in this PR.  Maybe I will wait for Guru to discuss with them or maybe Guru also signaled that we may implement a separate MCP server with tools specifically designed for open table then this is not going to be part of our catalog but we can implement it and give it for them to use.
Office TV Robot: So, I'm hearing we need to scope this better. This needs to be planned better. We don't actually know the full list of things we're doing yet.
Renato Byrro: I mean when I started we did not have a clear requirement from them.
Renato Byrro: It was just that Salesforce was very important for them during the PC and…
Renato Byrro: our MCP server was very limited. So I worked on making it a lot better regardless of open table and now today they came up with these soql requirements. So we're back into planning phase. I don't know maybe we should merge the tools that I have built and…
Office TV Robot: I think you should.
Renato Byrro: then if we decide to build something else for open table…
Office TV Robot: Yes. Agree.
Renato Byrro: then we open another PR for serious works.
Renato Byrro: Yeah.
Office TV Robot: So let's say that this one is actually over here, the PR you have ready. And then we're going to make in the ice box sales force SQL tools.
Office TV Robot: I'll leave this here for now.  Yeah.
Francisco Liberal: I may make a question.
Francisco Liberal: For example that I think that to take a lot of time not that's bad but is our quality control. I think that that's great. But maybe could you have someone in the team find someone would be someone not that we avoid having other people that will be more focused on that someone that's really good at QA but also good in agentic so he can improve the pipeline for the reviews and those kind of things because I think that it's kind of being a bottleneck like we are developers that that's cool we can do
Francisco Liberal: that might maybe have someone in the team just for this quality control would be really helpful that someone that's focuses on that because for example Eric will review my PR but he has also a bunch of other features to create to add and this person could for example explore tools for improve that while we are developing features as well not that we will just throw trash at him so he say that's bad or that's not good and just try again but I think as the bottleneck that I feel is more review and…
### 00:30:00
Francisco Liberal: more quality control I think maybe that would be useful have someone just focus on that
Office TV Robot: I agree with everything you said.
Office TV Robot: Reviewing in quality, reviewing both before planning and after is going to be the bottleneck 100%.
Francisco Liberal: Okay.
Office TV Robot: The intention is that this project that Eric and Nate are going to do together is going to make it so we are able to trust AI review. Lots more tests, a lot more integrations, lots more guidance, a lot more skills, a lot more all that stuff. so the intention is to speed up the review. If that doesn't work, then we'll start talking about hiring a PA team or something. Plan one is make it so figure out…
Office TV Robot: what it would take so that we could trust the robots.
Francisco Liberal: Yeah, because I think for the development you speed up really fast,…
Francisco Liberal: but you're not going so fast related to the quality control and that kind of is I don't know I feel that this also should be something like that.
Francisco Liberal: But if there is a project for that, I think that that's a good thing. Yeah.
Office TV Robot: That's the goal.
Office TV Robot: Who knows get there? And the goal by the end of the year is that anybody can write toolkits and we trust that it is good, not even customers, community members and so the goal for the end of the year is to figure out a pipeline robust and…
Francisco Liberal: That's my
Office TV Robot: good at testing that anybody can contribute. So building up to that is important. okay teal.
Teal Larson: Yes, I'll report back in an hour and…
Office TV Robot: This project is not giving me confidence. Excellent.
Teal Larson: a half. I think we're still in the process of defining what is strictly in scope. A lot of the issues and gaps that were identified in our initial pass were things that were actually documentation needs or…
Teal Larson: platform needs or things of that nature. And so we're working on splitting those apart, documenting them so that those things can get passed off to other proper teams and then scoping what is actually the best area for this team to focus in that was the outcome of our meeting last week and then we have another catch up I think today.
Office TV Robot: Makes sense.
Teal Larson: Yes. Shortly like an hour and a half.
Office TV Robot: Makes sense. this one's next.
Teal Larson: Developer onboarding. I have been working primarily on getting the CLI going with this.  So for context, what we're building is yeah, we can go to issues. That would be useful, I think. So there's some UI updates in the dashboard that give here are the steps for onboarding, right? You've created your account. Great job. Okay, let's go to the playground and execute a tool. So you're in the chat, you execute a tool and then you get a prompt to create your first agent.
Teal Larson: And the way in which you do that is through a new CLI. Thought about rolling it into the existing one. I can explain why we're not if that's useful to folks, but we'll create arcade agent, which I should probably make sure is actually available on npm. but we'll create arcade agent. You can run it and pass in a framework. so we have lang chain which will generate a Python agent.  We have versel AAI and MRA which will do TypeScript and you'll end up with a full example agent. That's the piece that I've been working on is the CLI and the agent generation and making sure that this will work with MCP gateways to see if there's any work I need to propagate back to the Tiger team. and then yeah, I've gained a lot of user empathy.
Teal Larson: There are a lot of differences in how these things are populated and my god GPT40 is so bad. I had the worst time. I was like why is my agent so dumb? The other one I wrote was great and then I was like I'm using GPT40. Okay. …
Teal Larson: so I just tested it and it worked almost as expected for both MRA and Verseli SDK. So, I need to check the lang chain one and…
### 00:35:00
Office TV Robot: Yes. Perfect.
Teal Larson: then I want to get this code checked in so I could get some feedback from Sergio on things like how we're templating and scaffolding some of the shared pieces of code and making sure that things are discoverable so people can customize and extend the agent that we are building for them to be the agent that they would like to take to production.  Yeah. Yeah.
Office TV Robot: And so by the time you're done, so you sign up, you're put into this workflow, and then the goal is that you have a real agent using arcade tools within 20 minutes or something like that. Very nice. Excellent.
Office TV Robot: And then let's talk about guard rails.
Teal Larson: So, I've been focusing primarily on the ones for the marketing site mainly because that was the place that I was getting pulled in the most and so I wanted to get a number of things in place which I have many that are finished and quite a few that are to do. This is kind of like a back burner as I have a couple minutes here and there project in between the onboarding and the MCP parody. I have a PR that adds better type checking and a PR that checks that we have the right number of H1s on a page,…
Office TV Robot: Makes sense.
Teal Larson: which in case you're wondering is exactly one. things like that. SEO technical I think actually got passed over to Sergio. I don't think I'm supposed to be getting tagged on those anymore if I remember Okay.
Office TV Robot: That is correct. Team no longer tools and DX. Goodbye. that project is for the group. There's AIO, which is like how do you get our stuff to appear in agentic search more often. So having good lms.txt, having a lot of content pointing back to us. But SEO is a very specific project.
Teal Larson: which I think still matters for AIO. Yeah.
Office TV Robot: That's the old way of doing things like why aren't we good in Google search? why we have broken links, robots.txts, that kind of stuff. Yes. Yes. Very much so.
Office TV Robot: Then we have these two projects that not us started.
Office TV Robot: I haven't seen anything about these two. There is actually a third one which is Yugabyte DB that EMTT put a PR up for Yu G. You bite three or…
Francisco Liberal: yoga. …
Francisco Liberal: you're probably I need some new project or…
Office TV Robot: eight bits. we'll find that later. but yeah, I haven't seen anything about those two. All right, let's put these both to on deck. So, I don't think they're working on them. cool. Okay, we have five in progress. Only five.
Francisco Liberal: to help
Francisco Liberal: one I think I will for nothing.
Office TV Robot: So you're almost done with Windows is what you're saying.
Francisco Liberal: Yeah. if Eric has nothing to reveal, I mean to fix, I think I will be done like tomorrow even today.
Office TV Robot: Perfect. I'm going to talk about the stand up. But first, Renado, you have a question.
Renato Byrro: Would the MC workflow stuff fall into the more build optimized tool kits from starter toolkits project or…
Renato Byrro: do we need a separate one? Okay, it's inside it.
Office TV Robot: Yes. No.
Office TV Robot: MC is not a part. It is a means to an end.
Office TV Robot: It is a theory that it might make this work. We do not have a project workflow engine on its own.
Renato Byrro: Okay,…
Renato Byrro: I think the only thing missing there is the Daytona MCP server,…
Renato Byrro: but we are about to get done with it. So, probably not worth it's already merged.
Office TV Robot: No,…
Office TV Robot: we very much should track it.
Office TV Robot: Let's just be lazy about it then. All right, this is a toolkit. Ranada, did you do it?
Renato Byrro: Yes. I mean I managed OPOS and…
Office TV Robot: The fact that I didn't know problem you take responsibility for any bugs.
Renato Byrro: GPT while they did it. I do.
### 00:40:00
Office TV Robot: Well done.
Renato Byrro: I do.
Office TV Robot: Okay, Francisco's question is what to do next? Is there something that needs help in progress list? Maybe Francisco could take unless Ronaldo's already in progress on the Microsoft utils applying that to other toolkits then it kind of sounds like Ronaldo you're spread fit on some other servers as well…
Office TV Robot: but maybe This one.
Renato Byrro: right now.
Renato Byrro: Yeah, where is There's the Morgan Stanley stuff now. Yeah. Yeah, we need to move this in progress. I have a bunch of things to do there. so your suggestion would be to maybe ask Francisco to apply the Microsoft use.
Renato Byrro: Is that it?
Office TV Robot: Yeah. Yeah,…
Office TV Robot: that's great. Yeah. Excellent.
Renato Byrro: Yeah, I think that would be fine. I can coordinate with him after the call.
Office TV Robot: This was a perfect outcome. Sharing the work, spreading it out. Thank you. So then at the end of the project review period like we did, now we do the normal standup.  So, anything we didn't talk about yet that you're working on, need help with or block by Dar, can you go first? I think I talked about everything. I'll probably bring it up in the platform instead, the platform stand up. But, the local dev for getting the engine and dashboard spun up.
Office TV Robot: I typically do make run and whenever there's a new dependency for the dashboard or for the engine, it just fails and then I have to go to that specific app and do bun install whatever the engine's make install thing. So it feels like our root level make file should just check to see that we have all the dependencies before running. So just local dev things. but just wanted to bring that up in case other people were experiencing that. Do we not have There's a top level make install, then there's a dev install. One of them will install literally everything. it'll go as far as installing git, So, it feels I don't know if it actually installs on git, but it goes far.
Office TV Robot: so there's no clear way to just install the dependencies needed to run these two things locally. there's a whole bunch of make commands and they're all confusing on which one does which. So t
Teal Larson: There's been ongoing discussion about the number of open front-end projects and so I've been working on creating tighter definition for the front end chapter and how we operate within the org and syncing with Sergio and Evan on that.  We're so special.
Office TV Robot: front of people are special.
Office TV Robot: I need to treat them that way. Francisco
Francisco Liberal: Yeah. Yeah.
Francisco Liberal: Let's see what I did not talk. the docs is already working that is in marish docs. So when there is some new updates to kit in both in the engine and then in the design systems it will generate automatically a documentation with a simple summary and in case you guys need to update the summary you can create a PR after that one is merged I think that would be the better way also when remove and those kind of things it's also create automatically so that's working.
Office TV Robot: Relax. Yes.
Francisco Liberal: Okay. The thing that I noticed that in the monor repo, Pobot is now doing PRs when it fights a bug.
Francisco Liberal: anyway that the guys can change the rules to allow us people to merge their own PRs in their own branches because I just saw I create a PR out of the postal bots fix and…
### 00:45:00
Francisco Liberal: then we require a review for someone to merge into my own branch. So I think that can be kind of annoying. So I think that could be useful for at least us to merge it in our own branch.
Office TV Robot: I lost.
Office TV Robot: Where'd it go? But good point. If it's not on main, you should be able to merge it. Or not going to mage. What repo was that for? Monor repo.
Office TV Robot: Welcome back, Francisco. Was that on the monor repo? your question.
Francisco Liberal: Yeah, I just create a PR for Eric review and…
Francisco Liberal: then it found a bug. It created PR. So it's useful. So I mean I have to click create PR because already found the fix then it created a PR but this PR to merge in my branch but it requires still other people's approval.  Okay.
Office TV Robot: That was not intentional. I'll check on that. We should only be requiring retrieval going to Check on that. And Ronaldo,…
Renato Byrro: So now just the regular updates. Is that it?
Office TV Robot: anything we didn't talk about already?
Renato Byrro: Okay. I think we've covered everything.
Office TV Robot: That's sweet.
Renato Byrro: Yeah, I think so. Salesforce, Daytona, Morgan Stanley, Microsoft Office. Yep.
Office TV Robot: And then I'll end with I am sorry that we are adding a little bit more process. I know this is going to make our standups a little more tedious, but we found three projects we didn't know about and Renado is doing four things at once. And so we do need to have a list in order of the things that we should be doing.
Office TV Robot: We're welcome to series A,…
Francisco Liberal: P
Office TV Robot: but I acknowledge that this is Ideally,…
Renato Byrro: How many…
Renato Byrro: how many things again can we have in progress?
Office TV Robot: one less than it's like I think the rule was three quarters times the number of people that are on the team. So, three we and…
Renato Byrro: Okay.
Office TV Robot: we're going to adjust all of this as we go. that was a starting guess. One less than humans because if you're all working on delivering, no one can help you review stuff. No call. No one can be planning. No one can be around for support. And so it's trying to acknowledge the truth that one human's worth of time is doing other stuff. And that's why we want to collaborate on finishing…
Francisco Liberal: Thanks.
Office TV Robot: what we have in progress to do more. we're increasing the project latency…
Office TV Robot: but to increase overall throughput or something. That's the intention. but we'll try it.
Renato Byrro: Yeah, I agree this is necessary.
Office TV Robot: We'll see how it goes.
Renato Byrro: I mean we can do so many things in parallel now with LLMs but we do not have the tooling to manage this in a sane way.
Office TV Robot: Yes. Yes.
Renato Byrro: We still don't have the tooling. So yeah,…
Office TV Robot: 
Office TV Robot: And …
Francisco Liberal: no it's not related to that I should have just raised my hands to the end of the startup when it's on a topic Okay,…
Renato Byrro: that said,
Office TV Robot: 
Office TV Robot: what do we do? Okay. yeah.
Teal Larson: I have to hop off.
Teal Larson: I have another meeting. I
Francisco Liberal: I'll finish. Okay, so my question is Idol if you could write for us at least for me I want one letter so I can show it to the border offse when I cross the …
Office TV Robot: He wants a letter officially from arcade that he can show when he's entering US. for the hackathon. Yeah. Yes.
Francisco Liberal: the last time that the guy asked me, so that might be useful.
Office TV Robot: I will do that. pizza letter and…
Francisco Liberal: Actually, I think I advise also for the other guys…
Office TV Robot: then I will do that.
Francisco Liberal: if they are coming from other cultures that might be helpful. I don't know.  At least the guy asked me was my first time so I don't know if that will change. Okay, thank you guys.
Office TV Robot: We're done. I think so. All right. Cool. Thank you everybody.
### Meeting ended after 00:55:03 👋
_This editable transcript was computer generated and might contain errors. People can also change the text after it was created._

