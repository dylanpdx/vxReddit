#!/bin/bash
set -euo pipefail

domain=https://vxreddit.com/
print_only=false

while getopts "d:n" opt; do
    case "$opt" in
        d) domain=$OPTARG ;;
        n) print_only=true ;;
        *) exit 1 ;;
    esac
done
shift $((OPTIND - 1))

declare -A tests=(
    [text]=https://www.reddit.com/r/RemarkableTablet/comments/1twzgb0/a_few_words_on_the_pure/
    [text-media]=https://www.reddit.com/r/RemarkableTablet/comments/1u6ep5a/introducing_our_new_team_account_328_beta/
    [text-titleonly]=https://www.reddit.com/r/AskReddit/comments/1ujr8do/us_supreme_court_in_63_ruling_upholds_birthright/
    [text-same]=https://www.reddit.com/user/Tight-Scientist-1031/comments/1umk3yl/the_title_and_body_text_is_the_same/

    [link]=https://www.reddit.com/r/news/comments/1ujr690/supreme_court_upholds_birthright_citizenship_on/
    [link-nohint]=https://www.reddit.com/r/pics/comments/5sfexx/this_is_shelia_fredrick_a_flight_attendant_she/
    [link-youtube]=https://www.reddit.com/r/videos/comments/88ll08/this_is_what_happens_when_one_company_owns_dozens/

    [image]=https://www.reddit.com/r/RemarkableTablet/comments/1uhyao1/morning_vibes/
    [image-caption]=https://www.reddit.com/r/RemarkableTablet/comments/1twq6mi/how_i_read_news_now/
    [image-gif]=https://www.reddit.com/r/gifs/comments/1u22nvz/eepy_frog/
    [image-gif-caption]=https://www.reddit.com/user/Tight-Scientist-1031/comments/1umk6d1/title/

    [gallery]=https://www.reddit.com/r/RemarkableTablet/comments/1ulibqk/one_dillion_dots_later_and_this_is_done/
    [gallery-caption]=https://www.reddit.com/r/RemarkableTablet/comments/1u25zob/remarkable_drawings/
    [gallery-gif]=https://www.reddit.com/r/Blockbench/comments/1uk334v/skeleton_knight/
    [gallery-gif-caption]=https://www.reddit.com/user/Tight-Scientist-1031/comments/1umkdpx/title/

    [video]=https://www.reddit.com/r/nextfuckinglevel/comments/1ukshul/2_people_have_climbed_the_empire_state_building/
    [video-caption]=https://www.reddit.com/r/RemarkableTablet/comments/1u9yfdg/received_beta_328_and_its_awesome_so_far/
    [video-noaudio]=https://www.reddit.com/r/IdiotsInCars/comments/1uk33rt/oc_a_bad_driver_never_misses_a_chance_to_be_polite/

    [reply]=https://www.reddit.com/r/RemarkableTablet/comments/1ulad9y/comment/ov38mit/
    [reply-media]=https://www.reddit.com/r/RemarkableTablet/comments/1ulad9y/comment/ov8ogh1/

    [other-noauthor]=https://www.reddit.com/r/pics/comments/i3izcv/first_day_of_school_in_a_georgia_town_one_of_the/
    [other-deleted]=https://www.reddit.com/user/Tight-Scientist-1031/comments/1umktwo/deleted_post/
    [other-removed]=https://www.reddit.com/r/whatisit/comments/1uhk9xo/what_on_earth_is_this/
    [other-user]=https://www.reddit.com/user/Tight-Scientist-1031/comments/1umks6t/title/
    [other-u]=https://www.reddit.com/u/Tight-Scientist-1031/comments/1umks6t/title/
    [other-r]=https://www.reddit.com/r/Tight-Scientist-1031/comments/1umks6t/title/
    [other-r-u]=https://www.reddit.com/r/u_Tight-Scientist-1031/comments/1umks6t/title/
    [other-alwaysshowmedia]=https://www.reddit.com/r/news/comments/1ulikh0/vatican_excommunicates_all_members_of/

    [share-mobile]=https://www.reddit.com/r/RemarkableTablet/s/nZLEY6RQSC
    [share-short]=https://redd.it/1u6ep5a/
    [share-nosubreddit]=https://www.reddit.com/comments/1u6ep5a/
    [share-nosubreddit-reply]=https://www.reddit.com/comments/1u6ep5a/comment/ort6uxv/
    [share-nosubreddit-reply-slug]=https://www.reddit.com/comments/1u6ep5a/introducing_our_new_team_account_328_beta/ort6uxv/
    [share-noslug]=https://www.reddit.com/r/RemarkableTablet/comments/1u6ep5a/
    [share-reply-slug]=https://www.reddit.com/r/RemarkableTablet/comments/1u6ep5a/introducing_our_new_team_account_328_beta/ort6uxv/
    [share-title-comment]=https://www.reddit.com/r/RemarkableTablet/comments/1u6ep5a/comment/
    [share-title-commentid]=https://www.reddit.com/r/RemarkableTablet/comments/1u6ep5a/ort6uxv/
)

red='\e[0;31m'
green='\e[0;32m'
reset='\e[0m'

count=0
while IFS= read -r name; do
    url=${tests[$name]}
    url=${url#https://www.reddit.com/}
    url=${url#https://redd.it/}
    url=$domain$url

    if $print_only; then
        echo "$url"
        ((++count % 5 == 0)) && echo
        continue
    fi

    echo -n "$name - "

    set +e
    out=$(curl -fs "$url")
    status=$?
    set -e

    if [[ $status != 0 ]]; then
        echo -e "${red}failed${reset} ($status)"
        continue
    elif [[ $out == *'content="Unknown post type'* ]]; then
        echo -e "${red}failed${reset} (unknown)"
        continue
    elif [[ $out == *'content="Failed to get data from Reddit'* ]]; then
        echo -e "${red}failed${reset} (data)"
        continue
    elif [[ $out == *'content="Internal server error'* ]]; then
        echo -e "${red}failed${reset} (server)"
        continue
    fi

    echo -e "${green}success${reset}"
done < <(printf '%s\n' "${!tests[@]}" | sort)
