(ns gracie.routes
  (:require
    [gracie.routes.auth :as auth]
    [gracie.routes.home :as home]
    [gracie.routes.illustrations :as illustrations]
    [gracie.routes.sketchbook-samples :as sketchbook-samples]
    [gracie.routes.storyboards :as storyboards]
    [gracie.routes.comics :as comics]
    [gracie.routes.deploy :as deploy]))

(def routes
  {"/"                                     #'home/view
   "/illustrations/"                       #'illustrations/view
   "/sketchbook-samples/"                  #'sketchbook-samples/view
   "/comics/"                              #'comics/index-view
   "/comics/:slug/"                        #'comics/single-view
   "/comics/:slug/page/:page/"             #'comics/single-view
   "/storyboards/"                         #'storyboards/index-view
   "/storyboards/category/:category-slug/" #'storyboards/category-view
   "/storyboards/:storyboard-slug/"        #'storyboards/single-view
   "/auth/"                                #'auth/view
   "/logout/"                              #'auth/logout
   "/deploy/:deploy-key/"                  #'deploy/view
   "/deploy/log/"                          #'deploy/log-view})

