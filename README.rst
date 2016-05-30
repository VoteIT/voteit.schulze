Schulze Polls for VoteIT
========================

.. image:: https://travis-ci.org/VoteIT/voteit.schulze.png?branch=master
    :target: https://travis-ci.org/VoteIT/voteit.schulze

This is a plugin package for VoteIT that provides functionality
for regular Schulze, STV and PR polls.


Schulze Method
--------------

Single winner with proper analysis of how each proposal was picked.
Use this for most cases where you want a single winner.

More information: `<https://en.wikipedia.org/wiki/Schulze_method>`_


Schulze STV (Single Transferable Vote)
--------------------------------------

Use this for elections where you want 2 or more winners. It doesn't
rank the winners though, they're only displayed.

More information: `<http://en.wikipedia.org/wiki/Schulze_STV>`_


Schulze PR (Proportional Ranking)
---------------------------------

Use this if you want to sort proposals according to preference. It has no
winner, it only outputs the preferred order of all the voters.
It's very computationally heavy, and complexity increases exponentially with each
new proposal. Any more than 5-6 proposals may cause problems. Use carefully!
